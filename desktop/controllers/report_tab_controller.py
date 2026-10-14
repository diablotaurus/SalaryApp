from __future__ import annotations

from typing import Any, Optional

from api.salary_api import SalaryAPI
from api.settings_api import SettingsAPI
from core.config.settings import config
from core.exceptions import RECOVERABLE_EXCEPTIONS, to_app_error
from desktop.controllers.render_cache import RenderCache


class ReportTabController:
    def __init__(self, navigation: Any):
        self.navigation = navigation
        self.app = navigation.app
        self._charts_cache = RenderCache()

    def refresh_reports(self):
        try:
            years_response = SalaryAPI.get_years()
            if years_response and years_response.get("success"):
                years = years_response["data"]
                self.app.report_view.update_years_list(years)
                if years:
                    self.load_chart_data()
                else:
                    self._charts_cache.invalidate()
            else:
                self._charts_cache.invalidate()
                self.app.report_view.update_years_list([])
        except RECOVERABLE_EXCEPTIONS as exc:
            self._charts_cache.invalidate()
            app_exc = to_app_error(exc, "Не удалось обновить аналитику")
            self.navigation.show_message("Ошибка", app_exc.user_message, "error")
            self.app.report_view.update_years_list([])

    @staticmethod
    def _response_data(response: Any) -> Any:
        return response["data"] if response and response.get("success") else None

    def load_chart_data(self):
        selected_year = self.app.report_view.get_selected_year()

        # Сначала собираем все данные (это дёшево), затем перерисовываем графики,
        # только если данные изменились с прошлой отрисовки.
        charts = {
            "monthly": self._response_data(SalaryAPI.get_monthly_series_dto(selected_year)),
            "yearly": self._response_data(SalaryAPI.get_yearly_comparison_dto()),
            "growth": self._response_data(SalaryAPI.get_growth_rate_dto()),
            "average": self._response_data(SalaryAPI.get_average_by_month_dto()),
        }
        kpi = self._load_kpi_data(selected_year)

        render_key = (selected_year, charts, kpi)
        if self._charts_cache.is_current(render_key):
            return

        self.app.report_view.update_monthly_chart(charts["monthly"])
        self.app.report_view.update_yearly_chart(charts["yearly"])
        self.app.report_view.update_growth_chart(charts["growth"])
        self.app.report_view.update_average_chart(charts["average"])
        self.app.report_view.update_kpi(**kpi)

        self._charts_cache.remember(render_key)

    def _load_kpi_data(self, selected_year: Optional[int]) -> dict[str, Any]:
        """Собрать аргументы для панели KPI (без обращения к представлению)."""
        summary = None
        best_month = None
        best_year = None
        show_best_year_always = True
        currency = config.app.currency

        settings_response = SettingsAPI.get_settings()
        if isinstance(settings_response, dict) and settings_response.get("success"):
            settings = settings_response.get("data", {})
            raw_value = settings.get("show_best_year_always", "1")
            show_best_year_always = str(raw_value).lower() in ("true", "1", "yes", "y")
            currency = str(settings.get("currency", currency))

        stats_response = SalaryAPI.get_statistics(selected_year)
        if isinstance(stats_response, dict) and stats_response.get("success"):
            summary = stats_response.get("data")

        if selected_year:
            salaries_response = SalaryAPI.get_salaries_by_year(selected_year)
            if isinstance(salaries_response, dict) and salaries_response.get("success") and salaries_response.get("data"):
                records = salaries_response.get("data", [])
                best_record = max(
                    records,
                    key=lambda item: (item.get("advance", 0) or 0) + (item.get("salary", 0) or 0),
                )
                best_month = {
                    "year": best_record.get("year"),
                    "month_name": best_record.get("month_name", ""),
                    "total": (best_record.get("advance", 0) or 0) + (best_record.get("salary", 0) or 0),
                }
            if show_best_year_always:
                best_response = SalaryAPI.get_best_periods()
                if isinstance(best_response, dict) and best_response.get("success"):
                    best_year = best_response.get("data", {}).get("best_year")
        else:
            best_response = SalaryAPI.get_best_periods()
            if isinstance(best_response, dict) and best_response.get("success"):
                best_month = best_response.get("data", {}).get("best_month")
                best_year = best_response.get("data", {}).get("best_year")

        show_best_year = show_best_year_always or not selected_year
        return {
            "summary": summary,
            "best_month": best_month,
            "best_year": best_year,
            "selected_year": selected_year,
            "show_best_year_always": show_best_year,
            "currency": currency,
        }

    def on_year_selected(self, _year: int):
        self.load_chart_data()

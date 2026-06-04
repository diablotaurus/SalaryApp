from __future__ import annotations

from typing import Any, Optional

from api.salary_api import SalaryAPI
from api.settings_api import SettingsAPI
from core.exceptions import RECOVERABLE_EXCEPTIONS, to_app_error


class ReportTabController:
    def __init__(self, navigation: Any):
        self.navigation = navigation
        self.app = navigation.app

    def refresh_reports(self):
        try:
            years_response = SalaryAPI.get_years()
            if years_response and years_response.get("success"):
                years = years_response["data"]
                self.app.report_view.update_years_list(years)
                if years:
                    self.load_chart_data()
            else:
                self.app.report_view.update_years_list([])
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Не удалось обновить аналитику")
            self.navigation.show_message("Ошибка", app_exc.user_message, "error")
            self.app.report_view.update_years_list([])

    def load_chart_data(self):
        selected_year = self.app.report_view.get_selected_year()

        monthly_response = SalaryAPI.get_monthly_series_dto(selected_year)
        self.app.report_view.update_monthly_chart(
            monthly_response["data"] if monthly_response and monthly_response.get("success") else None
        )

        yearly_response = SalaryAPI.get_yearly_comparison_dto()
        self.app.report_view.update_yearly_chart(
            yearly_response["data"] if yearly_response and yearly_response.get("success") else None
        )

        growth_response = SalaryAPI.get_growth_rate_dto()
        self.app.report_view.update_growth_chart(
            growth_response["data"] if growth_response and growth_response.get("success") else None
        )

        avg_response = SalaryAPI.get_average_by_month_dto()
        self.app.report_view.update_average_chart(
            avg_response["data"] if avg_response and avg_response.get("success") else None
        )

        self._load_kpi_data(selected_year)

    def _load_kpi_data(self, selected_year: Optional[int]):
        summary = None
        best_month = None
        best_year = None
        show_best_year_always = True

        settings_response = SettingsAPI.get_setting("show_best_year_always", True)
        if isinstance(settings_response, dict) and settings_response.get("success"):
            raw_value = settings_response.get("data", {}).get("value", True)
            show_best_year_always = str(raw_value).lower() in ("true", "1", "yes", "y")

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
        if hasattr(self.app, "report_view"):
            self.app.report_view.update_kpi(
                summary,
                best_month,
                best_year,
                selected_year,
                show_best_year_always=show_best_year,
            )

    def on_year_selected(self, _year: int):
        self.load_chart_data()

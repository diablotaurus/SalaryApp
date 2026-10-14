"""
Public Salary API facade.
"""
from __future__ import annotations

from api.salary_api_modules import analytics, commands, maintenance, queries
from core.exceptions import RECOVERABLE_EXCEPTIONS, to_app_error
from core.services.salary_service import SalaryService


class SalaryAPI:
    """Backwards-compatible facade for salary use-cases."""

    @staticmethod
    def add_salary(
        year: int,
        month: int,
        advance: float,
        salary: float,
        advance_date: str | None = None,
        salary_date: str | None = None,
    ) -> dict:
        # Kept in facade for backward compatibility with tests that patch
        # api.salary_api.SalaryService.add_salary.
        try:
            salary_obj = SalaryService.add_salary(
                year,
                month,
                advance,
                salary,
                advance_date=advance_date,
                salary_date=salary_date,
            )
            return {
                "success": True,
                "data": salary_obj.to_dict(),
                "message": "Данные успешно сохранены",
            }
        except ValueError as exc:
            return {"success": False, "error": str(exc), "message": str(exc)}
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Ошибка при сохранении данных")
            return {
                "success": False,
                "error": str(app_exc),
                "message": app_exc.user_message,
            }

    @staticmethod
    def validate_payment_date(value: str, field_label: str = "даты") -> dict:
        """Проверить дату выплаты по тем же правилам, что и при сохранении записи."""
        try:
            parsed = SalaryService.parse_payment_date(value, field_label)
        except ValueError as exc:
            return {"success": False, "error": str(exc), "message": str(exc)}
        return {"success": True, "data": parsed.strftime("%d.%m.%Y") if parsed else None}

    @staticmethod
    def get_salary(year: int, month: int) -> dict:
        return queries.get_salary(year, month)

    @staticmethod
    def get_current_period() -> dict:
        year, month = SalaryService.get_current_period()
        return {"success": True, "data": {"year": year, "month": month}}

    @staticmethod
    def get_all_salaries() -> dict:
        return queries.get_all_salaries()

    @staticmethod
    def get_all_grouped_by_year() -> dict:
        return queries.get_all_grouped_by_year()

    @staticmethod
    def get_salaries_by_year(year: int) -> dict:
        return queries.get_salaries_by_year(year)

    @staticmethod
    def get_years() -> dict:
        return queries.get_years()

    @staticmethod
    def get_year_summary(year: int) -> dict:
        return queries.get_year_summary(year)

    @staticmethod
    def get_statistics(year: int | None = None) -> dict:
        return analytics.get_statistics(year)

    @staticmethod
    def get_best_periods() -> dict:
        return analytics.get_best_periods()

    @staticmethod
    def get_monthly_series_dto(year: int | None = None) -> dict:
        return analytics.get_monthly_series_dto(year)

    @staticmethod
    def get_yearly_comparison_dto() -> dict:
        return analytics.get_yearly_comparison_dto()

    @staticmethod
    def get_growth_rate_dto() -> dict:
        return analytics.get_growth_rate_dto()

    @staticmethod
    def get_average_by_month_dto() -> dict:
        return analytics.get_average_by_month_dto()

    @staticmethod
    def export_data(format_type: str = "csv") -> dict:
        return maintenance.export_data(format_type)

    @staticmethod
    def create_backup(comment: str = "") -> dict:
        return maintenance.create_backup(comment)

    @staticmethod
    def list_backups() -> dict:
        return maintenance.list_backups()

    @staticmethod
    def restore_backup(reference: str) -> dict:
        return maintenance.restore_backup(reference)

    @staticmethod
    def delete_backup(reference: str) -> dict:
        return maintenance.delete_backup(reference)

    @staticmethod
    def delete_year(year: int) -> dict:
        return commands.delete_year(year)

    @staticmethod
    def delete_salary(year: int, month: int) -> dict:
        return commands.delete_salary(year, month)

from __future__ import annotations

from core.services.salary_service import SalaryService
from api.common import execute_with_default_error, failure, success


def get_salary(year: int, month: int) -> dict:
    def _action() -> dict:
        salary = SalaryService.get_salary(year, month)
        if salary:
            return success(salary.to_dict())
        return failure(
            message=f"Данные за {month}.{year} не найдены",
            error="Данные не найдены",
        )

    return execute_with_default_error(_action, "Ошибка при получении данных")


def get_all_salaries() -> dict:
    def _action() -> dict:
        salaries = SalaryService.get_all_salaries()
        payload = [item.to_dict() for item in salaries]
        return success(payload, count=len(payload))

    return execute_with_default_error(_action, "Ошибка при получении данных")


def get_all_grouped_by_year() -> dict:
    def _action() -> dict:
        data = SalaryService.get_all_grouped_by_year()
        return success(data, count=len(data))

    return execute_with_default_error(
        _action,
        "Ошибка при получении сгруппированных данных по годам",
    )


def get_salaries_by_year(year: int) -> dict:
    def _action() -> dict:
        salaries = SalaryService.get_salaries_by_year(year)
        payload = [item.to_dict() for item in salaries]
        return success(payload, count=len(payload), year=year)

    return execute_with_default_error(
        _action,
        f"Ошибка при получении данных за {year} год",
    )


def get_years() -> dict:
    def _action() -> dict:
        years = SalaryService.get_years()
        return success(years, count=len(years))

    return execute_with_default_error(_action, "Ошибка при получении списка лет")


def get_year_summary(year: int) -> dict:
    def _action() -> dict:
        summary = SalaryService.get_year_summary(year)
        data = {
            "year": summary.year,
            "total_advance": summary.total_advance,
            "total_salary": summary.total_salary,
            "total": summary.total,
            "average_monthly": summary.average_monthly,
            "records": [item.to_dict() for item in summary.records],
            "month_details": summary.month_details,
        }
        return success(data)

    return execute_with_default_error(_action, f"Ошибка при получении сводки за {year} год")

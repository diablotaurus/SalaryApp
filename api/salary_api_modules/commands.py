from __future__ import annotations

from core.exceptions import RECOVERABLE_EXCEPTIONS, to_app_error
from core.services.salary_service import SalaryService
from api.common import execute_with_default_error, failure, success


def add_salary(
    year: int,
    month: int,
    advance: float,
    salary: float,
    advance_date: str | None = None,
    salary_date: str | None = None,
) -> dict:
    try:
        salary_obj = SalaryService.add_salary(
            year,
            month,
            advance,
            salary,
            advance_date=advance_date,
            salary_date=salary_date,
        )
        return success(salary_obj.to_dict(), message="Данные успешно сохранены")
    except ValueError as exc:
        return failure(str(exc), error=str(exc))
    except RECOVERABLE_EXCEPTIONS as exc:
        app_exc = to_app_error(exc, "Ошибка при сохранении данных")
        return failure(app_exc.user_message, error=str(app_exc))


def delete_year(year: int) -> dict:
    def _action() -> dict:
        is_deleted = SalaryService.delete_year(year)
        if is_deleted:
            return success({"year": year}, message=f"Данные за {year} год успешно удалены")
        return failure(
            f"Не удалось удалить данные за {year} год",
            error="Ошибка удаления",
        )

    return execute_with_default_error(_action, f"Ошибка при удалении данных за {year} год")


def delete_salary(year: int, month: int) -> dict:
    def _action() -> dict:
        is_deleted = SalaryService.delete_salary(year, month)
        if is_deleted:
            return success(
                {"year": year, "month": month, "deleted": True},
                message=f"Данные за {month:02d}.{year} успешно удалены",
            )
        return success(
            {"year": year, "month": month, "deleted": False},
            message=f"Данные за {month:02d}.{year} уже отсутствуют",
        )

    return execute_with_default_error(
        _action,
        f"Ошибка при удалении данных за {month:02d}.{year}",
    )

from __future__ import annotations

from core.services.salary_service import SalaryService
from core.services.statistics_service import StatisticsService
from api.common import execute_with_default_error, success


def get_statistics(year: int | None = None) -> dict:
    return execute_with_default_error(
        lambda: success(StatisticsService.get_summary_statistics(year)),
        "Ошибка при получении статистики",
    )


def compare_with_recent_average(year: int, month: int) -> dict:
    """Сумма месяца против среднего за предыдущий год (data=None — сравнивать не с чем)."""
    return execute_with_default_error(
        lambda: success(StatisticsService.compare_with_recent_average(year, month)),
        "Ошибка при сравнении месяца со средним",
    )


def forecast_year(year: int) -> dict:
    """Прогноз итога текущего года (data=None — прогноза нет)."""
    return execute_with_default_error(
        lambda: success(StatisticsService.forecast_year(year)),
        "Ошибка при расчёте прогноза",
    )


def compare_year_to_date(year: int) -> dict:
    """Год к году за тот же период (data=None — сравнивать не с чем)."""
    return execute_with_default_error(
        lambda: success(StatisticsService.compare_year_to_date(year)),
        "Ошибка при сравнении с прошлым годом",
    )


def get_records() -> dict:
    return execute_with_default_error(
        lambda: success(StatisticsService.get_records()),
        "Ошибка при подсчёте рекордов",
    )


def get_best_periods() -> dict:
    return execute_with_default_error(
        lambda: success(StatisticsService.get_best_periods()),
        "Ошибка при получении лучших периодов",
    )


def get_monthly_series_dto(year: int | None = None) -> dict:
    def _action() -> dict:
        data = SalaryService.get_monthly_series_dto(year)
        return success(data, year=year)

    return execute_with_default_error(_action, "Ошибка при формировании DTO месячного графика")


def get_yearly_comparison_dto() -> dict:
    return execute_with_default_error(
        lambda: success(StatisticsService.get_yearly_comparison_dto()),
        "Ошибка при формировании DTO сравнения по годам",
    )


def get_growth_rate_dto() -> dict:
    return execute_with_default_error(
        lambda: success(StatisticsService.get_growth_rate_dto()),
        "Ошибка при формировании DTO темпов роста",
    )


def get_average_by_month_dto() -> dict:
    return execute_with_default_error(
        lambda: success(StatisticsService.get_average_by_month_dto()),
        "Ошибка при формировании DTO средних значений",
    )

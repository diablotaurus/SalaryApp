import pytest

from datetime import datetime, timedelta

from core.models.salary import Salary
from core.services.salary_service import SalaryService
from core.services.statistics_service import StatisticsService


def test_calculate_average_excludes_current_month_with_only_advance():
    records = [
        Salary(year=2026, month=2, advance=10000.0, salary=20000.0),
        Salary(year=2026, month=3, advance=15000.0, salary=0.0),
    ]

    result = StatisticsService.calculate_average_monthly_from_records(
        records,
        now=datetime(2026, 3, 6),
    )

    assert result == 30000.0


def test_calculate_average_includes_current_month_when_salary_exists():
    records = [
        Salary(year=2026, month=2, advance=10000.0, salary=20000.0),
        Salary(
            year=2026,
            month=3,
            advance=15000.0,
            salary=25000.0,
            salary_date=datetime(2026, 3, 5),
        ),
    ]

    result = StatisticsService.calculate_average_monthly_from_records(
        records,
        now=datetime(2026, 3, 6),
    )

    assert result == 35000.0


def test_calculate_average_excludes_month_until_salary_date_arrives():
    records = [
        Salary(
            year=2026,
            month=2,
            advance=10000.0,
            salary=20000.0,
            salary_date=datetime(2026, 3, 14),
        ),
    ]

    result = StatisticsService.calculate_average_monthly_from_records(
        records,
        now=datetime(2026, 3, 10),
    )

    assert result == 0.0


def test_calculate_average_includes_month_after_salary_date_arrives():
    records = [
        Salary(
            year=2026,
            month=2,
            advance=10000.0,
            salary=20000.0,
            salary_date=datetime(2026, 3, 14),
        ),
    ]

    result = StatisticsService.calculate_average_monthly_from_records(
        records,
        now=datetime(2026, 3, 16),
    )

    assert result == 30000.0


def test_calculate_average_legacy_without_salary_date_uses_past_month_rule():
    records = [
        Salary(year=2026, month=2, advance=10000.0, salary=20000.0, salary_date=None),
        Salary(year=2026, month=3, advance=15000.0, salary=25000.0, salary_date=None),
    ]

    result = StatisticsService.calculate_average_monthly_from_records(
        records,
        now=datetime(2026, 3, 20),
    )

    assert result == 30000.0


def test_get_summary_statistics_uses_unified_average_rule(monkeypatch):
    future_salary_date = datetime.now() + timedelta(days=5)
    records = [
        Salary(
            year=2026,
            month=2,
            advance=10000.0,
            salary=20000.0,
            salary_date=future_salary_date,
        ),
    ]

    monkeypatch.setattr(
        "core.services.statistics_service.SalaryRepository.get_statistics",
        lambda year: {
            "total_records": 1,
            "total_advance_all": 10000.0,
            "total_salary_all": 20000.0,
            "first_year": 2026,
            "last_year": 2026,
            "by_year": [{"year": 2026}],
        },
    )
    monkeypatch.setattr(
        "core.services.statistics_service.SalaryRepository.get_by_year",
        lambda year: records,
    )

    summary = StatisticsService.get_summary_statistics(2026)

    assert summary["average_monthly"] == 0.0
    assert summary["avg_monthly_total"] == 0.0


def test_average_by_month_skips_months_without_paid_salary(temp_db):
    # Тот же принцип, что у KPI «Среднемесячно»: месяц только с авансом
    # (зарплата ещё не выплачена) не занижает среднее на графике.
    SalaryService.add_salary(2024, 3, 1000.0, 3000.0, None, "25.03.2024")
    SalaryService.add_salary(2025, 3, 2000.0, 5000.0, None, "25.03.2025")
    SalaryService.add_salary(2025, 4, 1500.0, 0.0)  # зарплаты нет — месяц не учитывается

    items = {item["month"]: item for item in StatisticsService.get_average_by_month_dto()["items"]}

    assert set(items) == {3}
    assert items[3]["avg_advance"] == 1500.0
    assert items[3]["avg_salary"] == 4000.0
    assert items[3]["avg_total"] == 5500.0


def test_average_by_month_skips_salary_dated_in_future(temp_db):
    future = (datetime.now() + timedelta(days=30)).strftime("%d.%m.%Y")
    SalaryService.add_salary(2024, 5, 1000.0, 2000.0, None, "20.05.2024")
    SalaryService.add_salary(2025, 5, 9000.0, 9000.0, None, future)

    items = StatisticsService.get_average_by_month_dto()["items"]

    assert items == [{"month": 5, "avg_advance": 1000.0, "avg_salary": 2000.0, "avg_total": 3000.0}]


def _paid(year, month, total, day=25):
    # Зарплата выплачена (дата наступила) — месяц учитывается в средних
    return dict(year=year, month=month, advance=total / 2, salary=total / 2,
                salary_date=datetime(year, month, day).strftime("%d.%m.%Y"))


def _seed(*months):
    for item in months:
        SalaryService.add_salary(item["year"], item["month"], item["advance"], item["salary"], None, item["salary_date"])


def test_month_is_compared_with_previous_twelve_months(temp_db):
    _seed(*[_paid(2025, m, 100000.0) for m in range(1, 13)], _paid(2026, 1, 110000.0))
    _seed(_paid(2024, 12, 999999.0))  # 13 месяцев назад — вне окна

    result = StatisticsService.compare_with_recent_average(2026, 1, now=datetime(2026, 2, 1))

    assert result["months"] == 12
    assert result["average"] == 100000.0
    assert round(result["percent"], 6) == 10.0


def test_unpaid_month_or_short_history_is_not_compared(temp_db):
    _seed(_paid(2026, 1, 100000.0), _paid(2026, 2, 100000.0), _paid(2026, 3, 120000.0))
    SalaryService.add_salary(2026, 4, 50000.0, 0.0)  # только аванс

    assert StatisticsService.compare_with_recent_average(2026, 4, now=datetime(2026, 5, 1)) is None
    # для марта до него всего 2 выплаченных месяца — сравнивать рано
    assert StatisticsService.compare_with_recent_average(2026, 3, now=datetime(2026, 5, 1)) is None
    assert StatisticsService.compare_with_recent_average(2030, 1) is None


def test_percent_change():
    assert StatisticsService.percent_change(110, 100) == pytest.approx(10.0)
    assert StatisticsService.percent_change(5, 0) is None

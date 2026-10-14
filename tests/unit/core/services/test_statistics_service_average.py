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

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from core.repositories.salary_repository import SalaryRepository
from core.repositories.analytics_repository import AnalyticsRepository
from core.models.salary import Salary
from core.database.connection import DatabaseConnection
from core.services.salary_service import SalaryService


def test_salary_repository_save_get_delete_crud(temp_db):
    salary = Salary(
        year=2025,
        month=7,
        advance=15000.0,
        salary=25000.0,
        advance_date=datetime.strptime("10.07.2025", "%d.%m.%Y"),
        salary_date=datetime.strptime("25.07.2025", "%d.%m.%Y"),
    )

    saved = SalaryRepository.save(salary)
    assert saved.id is not None

    by_period = SalaryRepository.get_by_year_month(2025, 7)
    assert by_period is not None
    assert by_period.advance == 15000.0
    assert by_period.salary == 25000.0
    assert by_period.advance_date.strftime("%d.%m.%Y") == "10.07.2025"
    assert by_period.salary_date.strftime("%d.%m.%Y") == "25.07.2025"

    by_year = SalaryRepository.get_by_year(2025)
    assert len(by_year) == 1
    assert by_year[0].month == 7

    deleted = SalaryRepository.delete_by_year_month(2025, 7)
    assert deleted is True
    assert SalaryRepository.get_by_year_month(2025, 7) is None


def test_salary_repository_persists_integer_kopecks(temp_db):
    SalaryRepository.save(Salary(year=2025, month=8, advance=123.45, salary=678.9))

    conn = DatabaseConnection.get_connection()
    row = conn.execute(
        "SELECT advance, salary, typeof(advance), typeof(salary) FROM salaries"
    ).fetchone()

    assert tuple(row) == (12345, 67890, "integer", "integer")


def test_upsert_keeps_one_record_per_period(temp_db):
    first = SalaryRepository.upsert(
        Salary(year=2025, month=9, advance=100.0, salary=200.0)
    )
    second = SalaryRepository.upsert(
        Salary(year=2025, month=9, advance=300.0, salary=400.0)
    )

    conn = DatabaseConnection.get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM salaries WHERE year = 2025 AND month = 9"
    ).fetchone()[0]

    assert first.id == second.id
    assert count == 1
    assert second.advance == 300.0


def test_concurrent_upserts_do_not_create_duplicate_periods(temp_db):
    def write_salary(index):
        try:
            return SalaryService.add_salary(
                2026,
                3,
                1000 + index,
                2000 + index,
            ).id
        finally:
            DatabaseConnection.close_connection()

    with ThreadPoolExecutor(max_workers=8) as executor:
        ids = list(executor.map(write_salary, range(16)))

    conn = DatabaseConnection.get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM salaries WHERE year = 2026 AND month = 3"
    ).fetchone()[0]

    assert count == 1
    assert len(set(ids)) == 1


def test_analytics_returns_rubles_from_kopeck_storage(temp_db):
    SalaryService.add_salary(2026, 1, 100.25, 200.75)
    SalaryService.add_salary(2026, 2, 300.5, 400.5)

    yearly = AnalyticsRepository.get_yearly_totals()
    best_year = AnalyticsRepository.get_best_year()

    assert yearly == [
        {
            "year": 2026,
            "total_advance": 400.75,
            "total_salary": 601.25,
            "total_extras": 0.0,
            "total": 1002.0,
            "months_count": 2,
        }
    ]
    assert best_year == {"year": 2026, "total": 1002.0}

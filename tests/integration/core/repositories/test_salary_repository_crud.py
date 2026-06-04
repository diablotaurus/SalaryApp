from datetime import datetime

from core.repositories.salary_repository import SalaryRepository
from core.models.salary import Salary


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


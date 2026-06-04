from datetime import datetime

import pytest

from core.models.salary import Salary
from core.services.salary_service import SalaryService


def test_add_salary_creates_new_record(monkeypatch):
    captured = {}

    def fake_get_by_year_month(year, month):
        return None

    def fake_save(salary_obj):
        salary_obj.id = 101
        captured["saved"] = salary_obj
        return salary_obj

    monkeypatch.setattr(
        "core.services.salary_service.SalaryRepository.get_by_year_month",
        fake_get_by_year_month,
    )
    monkeypatch.setattr(
        "core.services.salary_service.SalaryRepository.save",
        fake_save,
    )

    created = SalaryService.add_salary(
        2025, 3, 10000.0, 20000.0, "10.03.2025", "25.03.2025"
    )

    assert created.id == 101
    assert captured["saved"].year == 2025
    assert captured["saved"].month == 3
    assert captured["saved"].advance_date.strftime("%d.%m.%Y") == "10.03.2025"
    assert captured["saved"].salary_date.strftime("%d.%m.%Y") == "25.03.2025"


def test_add_salary_updates_existing_record_without_overwriting_dates_on_empty_input(monkeypatch):
    existing = Salary(
        id=7,
        year=2025,
        month=4,
        advance=5000.0,
        salary=12000.0,
        advance_date=datetime.strptime("11.04.2025", "%d.%m.%Y"),
        salary_date=datetime.strptime("26.04.2025", "%d.%m.%Y"),
    )

    def fake_get_by_year_month(year, month):
        return existing

    def fake_save(salary_obj):
        return salary_obj

    monkeypatch.setattr(
        "core.services.salary_service.SalaryRepository.get_by_year_month",
        fake_get_by_year_month,
    )
    monkeypatch.setattr(
        "core.services.salary_service.SalaryRepository.save",
        fake_save,
    )

    updated = SalaryService.add_salary(2025, 4, 7000.0, 15000.0, "", "")

    assert updated.advance == 7000.0
    assert updated.salary == 15000.0
    assert updated.advance_date.strftime("%d.%m.%Y") == "11.04.2025"
    assert updated.salary_date.strftime("%d.%m.%Y") == "26.04.2025"


def test_add_salary_invalid_date_raises_value_error(monkeypatch):
    monkeypatch.setattr(
        "core.services.salary_service.SalaryRepository.get_by_year_month",
        lambda year, month: None,
    )

    with pytest.raises(ValueError):
        SalaryService.add_salary(2025, 5, 1000.0, 2000.0, "99.99.2025", None)


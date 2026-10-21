
import pytest

from core.services.salary_service import SalaryService


def test_add_salary_creates_new_record(monkeypatch):
    captured = {}

    def fake_upsert(salary_obj, **flags):
        salary_obj.id = 101
        captured["saved"] = salary_obj
        captured["flags"] = flags
        return salary_obj

    monkeypatch.setattr(
        "core.services.salary_service.SalaryRepository.upsert",
        fake_upsert,
    )

    created = SalaryService.add_salary(
        2025, 3, 10000.0, 20000.0, "10.03.2025", "25.03.2025"
    )

    assert created.id == 101
    assert captured["saved"].year == 2025
    assert captured["saved"].month == 3
    assert captured["saved"].advance_date.strftime("%d.%m.%Y") == "10.03.2025"
    assert captured["saved"].salary_date.strftime("%d.%m.%Y") == "25.03.2025"


def _save_april_with_dates():
    SalaryService.add_salary(2025, 4, 5000.0, 12000.0, "11.04.2025", "26.04.2025")


def test_add_salary_keeps_dates_when_not_provided(temp_db):
    # None — дата не передана: бот при ответе «-», API-запрос без поля даты.
    _save_april_with_dates()

    updated = SalaryService.add_salary(2025, 4, 7000.0, 15000.0, None, None)

    assert updated.advance == 7000.0
    assert updated.salary == 15000.0
    assert updated.advance_date.strftime("%d.%m.%Y") == "11.04.2025"
    assert updated.salary_date.strftime("%d.%m.%Y") == "26.04.2025"


@pytest.mark.parametrize("empty", ["", "   "])
def test_add_salary_clears_dates_emptied_in_form(temp_db, empty):
    # Формы desktop и web подставляют сохранённые даты в поля:
    # пустое поле означает, что пользователь стёр дату.
    _save_april_with_dates()

    updated = SalaryService.add_salary(2025, 4, 7000.0, 15000.0, empty, empty)

    assert updated.advance_date is None
    assert updated.salary_date is None
    assert SalaryService.get_salary(2025, 4).advance_date is None


def test_add_salary_clears_only_the_emptied_date(temp_db):
    _save_april_with_dates()

    updated = SalaryService.add_salary(2025, 4, 5000.0, 12000.0, "", None)

    assert updated.advance_date is None
    assert updated.salary_date.strftime("%d.%m.%Y") == "26.04.2025"


def test_add_salary_invalid_date_raises_value_error():
    with pytest.raises(ValueError):
        SalaryService.add_salary(2025, 5, 1000.0, 2000.0, "99.99.2025", None)


@pytest.mark.parametrize(
    ("year", "month", "advance", "salary"),
    [
        (1999, 1, 1, 1),
        (2101, 1, 1, 1),
        (2025, 0, 1, 1),
        (2025, 13, 1, 1),
        (2025, 1, -1, 1),
        (2025, 1, 1, float("nan")),
    ],
)
def test_add_salary_rejects_invalid_domain_values(year, month, advance, salary):
    with pytest.raises(ValueError):
        SalaryService.add_salary(year, month, advance, salary)

from datetime import date, datetime

import pytest

from api.salary_api import SalaryAPI
from core.models.year import calculate_average_monthly
from core.repositories.analytics_repository import AnalyticsRepository
from core.services.extra_payment_service import ExtraPaymentService
from core.services.reminder_service import ADVANCE, PaymentReminderService
from core.services.salary_service import SalaryService
from core.services.statistics_service import StatisticsService


def _month(year=2026, month=8, advance=40000.0, salary=60000.0):
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    SalaryService.add_salary(year, month, advance, salary, f"28.{month:02}.{year}", f"14.{next_month:02}.{next_year}")


# --- Ввод и проверка ---------------------------------------------------------------------------


def test_extra_payment_is_added_to_month_total(temp_db):
    _month()

    payment = ExtraPaymentService.add(2026, 8, "vacation", 35000.0, "10.08.2026", "  отпуск  ")

    assert (payment.kind_name, payment.amount, payment.comment) == ("Отпускные", 35000.0, "отпуск")
    record = SalaryService.get_salary(2026, 8)
    assert (record.regular_total, record.extras_total, record.total) == (100000.0, 35000.0, 135000.0)
    assert record.to_dict()["total"] == 135000.0


@pytest.mark.parametrize(
    ("kind", "amount", "message"),
    [("salary", 1.0, "вид"), ("bonus", 0, "больше нуля"), ("bonus", -5, "отрицательной"), ("bonus", "abc", "Некорректная")],
)
def test_invalid_extra_payment_is_rejected(temp_db, kind, amount, message):
    with pytest.raises(ValueError, match=message):
        ExtraPaymentService.add(2026, 8, kind, amount)


def test_extra_without_salary_creates_month_and_reminders_still_work(temp_db):
    # Премия пришла в октябре раньше аванса: месяц появляется, аванс — нет
    for month in range(1, 10):
        _month(month=month)
    ExtraPaymentService.add(2026, 10, "bonus", 20000.0, "05.10.2026")

    record = SalaryService.get_salary(2026, 10)
    assert (record.advance, record.salary, record.total) == (0.0, 0.0, 20000.0)
    due = PaymentReminderService.due_reminders(SalaryService.get_all_salaries(), date(2026, 10, 28))
    assert [(r.kind, r.month) for r in due] == [(ADVANCE, 10)]


def test_deleting_last_extra_removes_empty_month_but_keeps_real_one(temp_db):
    _month()
    real = ExtraPaymentService.add(2026, 8, "bonus", 1.0)
    lone = ExtraPaymentService.add(2026, 10, "bonus", 1.0)

    assert ExtraPaymentService.delete(lone.id) is True
    assert ExtraPaymentService.delete(real.id) is True
    assert ExtraPaymentService.delete(real.id) is False

    assert SalaryService.get_salary(2026, 10) is None  # пустой месяц убран
    assert SalaryService.get_salary(2026, 8).extras_total == 0.0  # настоящий месяц остался


def test_month_with_note_is_not_removed_with_last_extra(temp_db):
    payment = ExtraPaymentService.add(2026, 10, "sick", 1.0)
    SalaryService.set_note(2026, 10, "больничный")

    ExtraPaymentService.delete(payment.id)

    assert SalaryService.get_salary(2026, 10).note == "больничный"


def test_deleting_month_or_year_removes_its_extras(temp_db):
    _month(month=8)
    _month(month=9)
    ExtraPaymentService.add(2026, 8, "bonus", 1.0)
    ExtraPaymentService.add(2026, 9, "bonus", 1.0)

    SalaryService.delete_salary(2026, 8)
    _month(month=8)  # месяц внесён заново — старая премия не «воскресает»
    assert SalaryService.get_salary(2026, 8).extras_total == 0.0

    SalaryService.delete_year(2026)
    assert ExtraPaymentService.get_by_year(2026) == []


# --- Итоги и средние ----------------------------------------------------------------------------


def test_totals_everywhere_include_extras(temp_db):
    _month(month=7)
    _month(month=8)
    ExtraPaymentService.add(2026, 8, "bonus", 50000.0)

    yearly = AnalyticsRepository.get_yearly_totals()[0]
    assert (yearly["total_extras"], yearly["total"]) == (50000.0, 250000.0)
    assert AnalyticsRepository.get_best_month()["month"] == 8
    year = SalaryService.get_year_with_all_months(2026)
    assert (year["summary"]["total"], year["summary"]["total_extras"]) == (250000.0, 50000.0)
    august = year["months"][7]
    assert (august["total"], august["extras_total"]) == (150000.0, 50000.0)
    assert [item["kind_name"] for item in august["extras"]] == ["Премия"]
    assert year["months"][6]["extras"] == []


def test_two_averages_regular_and_total(temp_db):
    _month(month=7)
    _month(month=8)
    ExtraPaymentService.add(2026, 8, "vacation", 40000.0)
    now = datetime(2026, 10, 1)

    records = SalaryService.get_salaries_by_year(2026)
    assert calculate_average_monthly(records, now) == 120000.0  # (100 000 + 140 000) / 2
    assert calculate_average_monthly(records, now, include_extras=False) == 100000.0
    summary = SalaryService.get_year_with_all_months(2026)["summary"]
    assert summary["regular_average_monthly"] == 100000.0


def test_summary_statistics_has_extras_and_regular_average(temp_db):
    _month(month=7)
    ExtraPaymentService.add(2026, 7, "other", 10000.0)

    summary = StatisticsService.get_summary_statistics(2026)

    assert (summary["total_extras"], summary["total_all"]) == (10000.0, 110000.0)
    assert summary["regular_average_monthly"] == 100000.0


# --- API ----------------------------------------------------------------------------------------


def test_api_add_list_delete(temp_db):
    added = SalaryAPI.add_extra_payment(2026, 8, "bonus", 12500.5, "20.08.2026", "квартальная")
    assert added["success"] and added["data"]["amount"] == 12500.5

    listed = SalaryAPI.get_extra_payments(2026, 8)
    assert [item["paid_date"] for item in listed["data"]] == ["20.08.2026"]

    assert SalaryAPI.delete_extra_payment(added["data"]["id"])["success"] is True
    assert SalaryAPI.delete_extra_payment(added["data"]["id"])["error"] == "not found"
    assert SalaryAPI.add_extra_payment(2026, 8, "bonus", 0)["success"] is False
    assert [k["name"] for k in SalaryAPI.get_extra_kinds()["data"]] == ["Отпускные", "Премия", "Больничные", "Прочее"]

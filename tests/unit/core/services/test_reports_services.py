from datetime import datetime, timezone

import pytest

from core.repositories.reminder_state_repository import ReminderStateRepository
from core.services.annual_report_service import AnnualReportService
from core.services.salary_service import SalaryService
from core.services.settings_service import SettingsService
from core.services.statistics_service import StatisticsService


def _add(year, month, advance, salary, salary_date=None):
    # По умолчанию зарплата пришла 14-го следующего месяца — месяц выплачен
    if salary and salary_date is None:
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        salary_date = f"14.{next_month:02}.{next_year}"
    SalaryService.add_salary(year, month, advance, salary, None, salary_date)


# --- Год к году за тот же период ------------------------------------------------------------


def test_year_to_date_compares_same_months(temp_db):
    for month in range(1, 13):
        _add(2025, month, 50000.0, 50000.0)
    for month in range(1, 10):
        _add(2026, month, 52000.0, 52000.0)
    _add(2026, 10, 30000.0, 0.0)  # октябрь — только аванс, в сравнение не попадает

    result = StatisticsService.compare_year_to_date(2026, now=datetime(2026, 10, 22))

    assert result["last_month"] == 9
    assert result["total"] == 9 * 104000.0
    assert result["previous_total"] == 9 * 100000.0
    assert result["percent"] == pytest.approx(4.0)


def test_year_to_date_needs_paid_months_and_previous_year(temp_db):
    _add(2026, 1, 1000.0, 0.0)
    assert StatisticsService.compare_year_to_date(2026, now=datetime(2026, 1, 30)) is None
    _add(2027, 1, 1000.0, 1000.0)
    assert StatisticsService.compare_year_to_date(2027, now=datetime(2027, 3, 1)) is not None
    assert StatisticsService.compare_year_to_date(2030) is None


# --- Рекорды ---------------------------------------------------------------------------------


def test_records(temp_db):
    for month in range(1, 13):
        _add(2025, month, 50000.0, 50000.0)  # полный год: 1 200 000
    _add(2025, 8, 90000.0, 90000.0)          # лучший месяц
    _add(2026, 1, 70000.0, 70000.0)          # неполный год, но выше среднее
    _add(2026, 2, 70000.0, 70000.0)

    records = StatisticsService.get_records()

    assert [(m["year"], m["month"], m["total"]) for m in records["top_months"]] == [
        (2025, 8, 180000.0), (2026, 2, 140000.0), (2026, 1, 140000.0),
    ]
    assert records["top_months"][0]["month_name"] == "Август"
    assert records["best_year"]["year"] == 2025  # неполный 2026 не участвует по сумме
    assert records["best_average_year"]["year"] == 2026


def test_records_empty(temp_db):
    assert StatisticsService.get_records() == {"top_months": [], "best_year": None, "best_average_year": None}


# --- Когда отправлять годовой итог ---------------------------------------------------------------


def _msk_evening(day, month=1, year=2027):
    return datetime(year, month, day, 16, 30, tzinfo=timezone.utc)  # 19:30 МСК


def test_annual_report_waits_for_december_salary(temp_db):
    for month in range(1, 12):
        _add(2026, month, 1.0, 1.0)
    _add(2026, 12, 1.0, 0.0)  # зарплата за декабрь ещё не пришла

    assert AnnualReportService.year_to_report(_msk_evening(10)) is None
    _add(2026, 12, 1.0, 1.0, "14.01.2027")
    assert AnnualReportService.year_to_report(_msk_evening(14)) == 2026


def test_annual_report_is_sent_by_25th_even_without_december(temp_db):
    _add(2026, 11, 1.0, 1.0)

    assert AnnualReportService.year_to_report(_msk_evening(24)) is None
    assert AnnualReportService.year_to_report(_msk_evening(25)) == 2026


def test_annual_report_only_once_in_january_evening_and_when_enabled(temp_db):
    _add(2026, 12, 1.0, 1.0, "14.01.2027")

    assert AnnualReportService.year_to_report(datetime(2027, 1, 20, 9, 0, tzinfo=timezone.utc)) is None  # день
    assert AnnualReportService.year_to_report(_msk_evening(20, month=2)) is None  # не январь

    SettingsService.set_setting("telegram_reminders", False)
    assert AnnualReportService.year_to_report(_msk_evening(20)) is None
    SettingsService.set_setting("telegram_reminders", True)

    assert AnnualReportService.year_to_report(_msk_evening(20)) == 2026
    AnnualReportService.mark_sent(2026)
    assert ReminderStateRepository.get_annual_sent() == 2026
    assert AnnualReportService.year_to_report(_msk_evening(21)) is None


def test_no_annual_report_without_data(temp_db):
    assert AnnualReportService.year_to_report(_msk_evening(25)) is None


# --- Прогноз года ----------------------------------------------------------------------------


def test_forecast_adds_average_for_remaining_months(temp_db):
    for month in range(1, 13):
        _add(2025, month, 50000.0, 50000.0)  # 100 000 в месяц
    for month in range(1, 10):
        _add(2026, month, 55000.0, 55000.0)  # 110 000 в месяц, январь–сентябрь
    _add(2026, 10, 55000.0, 0.0)  # октябрь — пока только аванс: считается оставшимся

    result = StatisticsService.forecast_year(2026, now=datetime(2026, 10, 22, tzinfo=timezone.utc))

    # среднее за 12 месяцев (окт 2025 – сен 2026): 3 × 100 000 + 9 × 110 000
    average = (3 * 100000.0 + 9 * 110000.0) / 12
    assert result["earned"] == 9 * 110000.0
    assert result["remaining_months"] == 3
    assert result["average"] == pytest.approx(average)
    assert result["forecast"] == pytest.approx(9 * 110000.0 + 3 * average)


def test_forecast_only_for_current_year_with_enough_history(temp_db):
    now = datetime(2026, 10, 22, tzinfo=timezone.utc)
    _add(2026, 8, 1.0, 1.0)
    _add(2026, 9, 1.0, 1.0, "14.10.2026")

    assert StatisticsService.forecast_year(2026, now) is None  # всего 2 выплаченных месяца
    _add(2026, 7, 1.0, 1.0)
    assert StatisticsService.forecast_year(2026, now) is not None
    assert StatisticsService.forecast_year(2025, now) is None  # прошлый год — уже не прогноз

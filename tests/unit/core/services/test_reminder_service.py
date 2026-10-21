from datetime import date, datetime, timezone

import pytest

from core.models.salary import Salary
from core.repositories.reminder_state_repository import ReminderStateRepository
from core.services.reminder_service import (
    ADVANCE,
    SALARY,
    PaymentReminderService,
    PaymentSchedule,
    Reminder,
)
from core.services.salary_service import SalaryService
from core.services.settings_service import SettingsService


def _month(year, month, advance=1000.0, salary=2000.0, advance_day=28, salary_day=14):
    """Как в реальной истории: аванс — в том же месяце, зарплата — в следующем."""
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    return Salary(
        year=year,
        month=month,
        advance=advance,
        salary=salary,
        advance_date=datetime(year, month, advance_day) if advance else None,
        salary_date=datetime(next_year, next_month, salary_day) if salary else None,
    )


def _history(months=6, **kwargs):
    # Январь–июнь 2026 полностью
    return [_month(2026, m, **kwargs) for m in range(1, months + 1)]


# --- Расписание по истории ----------------------------------------------------------


def test_schedule_is_learned_from_history():
    schedules = PaymentReminderService.learn_schedule(_history(), date(2026, 7, 20))

    assert schedules[ADVANCE] == PaymentSchedule(ADVANCE, 28, 0)
    assert schedules[SALARY] == PaymentSchedule(SALARY, 14, 1)


def test_schedule_follows_employer_moving_the_date():
    records = [_month(2026, m, advance_day=28) for m in (1, 2)] + [
        _month(2026, m, advance_day=25) for m in (3, 4, 5)
    ]

    assert PaymentReminderService.learn_schedule(records, date(2026, 6, 1))[ADVANCE].day == 25


def test_schedule_tie_prefers_most_recent_day():
    records = [_month(2026, 1, advance_day=27), _month(2026, 2, advance_day=28)]

    assert PaymentReminderService.learn_schedule(records, date(2026, 3, 1))[ADVANCE].day == 28


def test_schedule_defaults_without_dated_history():
    schedules = PaymentReminderService.learn_schedule([], date(2026, 7, 1))

    assert (schedules[ADVANCE].day, schedules[ADVANCE].lag) == (28, 0)
    assert (schedules[SALARY].day, schedules[SALARY].lag) == (14, 1)


def test_schedule_ignores_payments_older_than_a_year():
    old = [_month(2024, m, advance_day=10) for m in range(1, 13)]
    recent = [_month(2026, m, advance_day=28) for m in (1, 2)]

    assert PaymentReminderService.learn_schedule(old + recent, date(2026, 3, 1))[ADVANCE].day == 28


# --- Какие напоминания пора отправить ------------------------------------------------


def test_advance_reminder_on_payment_day_and_four_more_evenings():
    records = _history()  # за июль ничего нет
    due = [PaymentReminderService.due_reminders(records, date(2026, 7, day)) for day in range(27, 32)]

    assert due[0] == []  # 27-го ещё рано
    assert due[1] == [Reminder(ADVANCE, 2026, 7, date(2026, 7, 28), 1)]
    assert [r.evening for r in due[4]] == [4]


def test_advance_window_continues_into_next_month():
    records = _history()

    reminders = PaymentReminderService.due_reminders(records, date(2026, 8, 1))
    later = PaymentReminderService.due_reminders(records, date(2026, 8, 2))

    assert Reminder(ADVANCE, 2026, 7, date(2026, 7, 28), 5) in reminders
    assert all(r.kind != ADVANCE for r in later)  # шестого вечера нет


def test_salary_reminder_is_for_previous_month():
    records = _history()  # зарплата за июнь ещё не внесена (была бы 14.07)
    records[-1] = _month(2026, 6, salary=0)

    reminders = PaymentReminderService.due_reminders(records, date(2026, 7, 14))

    assert reminders == [Reminder(SALARY, 2026, 6, date(2026, 7, 14), 1)]


def test_no_reminder_when_payment_entered():
    records = _history() + [_month(2026, 7, salary=0)]  # аванс за июль внесён

    assert PaymentReminderService.due_reminders(records, date(2026, 7, 29)) == []


def test_snoozed_payment_is_not_reminded():
    snoozed = frozenset({(ADVANCE, 2026, 7)})

    assert PaymentReminderService.due_reminders(_history(), date(2026, 7, 28), snoozed) == []


def test_payment_day_is_clamped_to_short_month():
    records = [_month(2025, m, advance_day=30) for m in range(3, 13)] + [_month(2026, 1, advance_day=30)]

    reminders = PaymentReminderService.due_reminders(records, date(2026, 2, 28))

    assert reminders == [Reminder(ADVANCE, 2026, 2, date(2026, 2, 28), 1)]


@pytest.mark.parametrize(
    ("utc_time", "expected"),
    [
        (datetime(2026, 7, 28, 15, 59, tzinfo=timezone.utc), False),  # 18:59 МСК
        (datetime(2026, 7, 28, 16, 0, tzinfo=timezone.utc), True),    # 19:00 МСК
        (datetime(2026, 7, 28, 19, 59, tzinfo=timezone.utc), True),   # 22:59 МСК
        (datetime(2026, 7, 28, 20, 0, tzinfo=timezone.utc), False),   # 23:00 МСК
    ],
)
def test_send_window_is_evening_in_moscow(utc_time, expected):
    assert PaymentReminderService.is_send_time(utc_time) is expected


# --- С базой: включение, раз в вечер, «не напоминать» ---------------------------------

EVENING = datetime(2026, 7, 28, 16, 30, tzinfo=timezone.utc)  # 19:30 МСК, день аванса


def _seed_history():
    for record in _history():
        SalaryService.add_salary(
            record.year, record.month, record.advance, record.salary,
            record.advance_date.strftime("%d.%m.%Y"), record.salary_date.strftime("%d.%m.%Y"),
        )


def test_reminders_are_sent_once_per_evening(temp_db):
    _seed_history()

    first = PaymentReminderService.reminders_to_send(EVENING)
    PaymentReminderService.mark_sent(EVENING)
    second = PaymentReminderService.reminders_to_send(EVENING)

    assert [(r.kind, r.year, r.month) for r in first] == [(ADVANCE, 2026, 7)]
    assert second == []
    assert ReminderStateRepository.get_last_sent() == date(2026, 7, 28)


def test_reminders_can_be_turned_off(temp_db):
    _seed_history()
    assert SettingsService.get_setting("telegram_reminders") == "1"  # включено по умолчанию

    SettingsService.set_setting("telegram_reminders", False)

    assert PaymentReminderService.reminders_to_send(EVENING) == []


def test_snooze_is_stored_and_old_entries_pruned(temp_db):
    _seed_history()
    PaymentReminderService.snooze(SALARY, 2025, 1, EVENING)  # старше полугода — уйдёт
    PaymentReminderService.snooze(ADVANCE, 2026, 7, EVENING)

    assert ReminderStateRepository.get_snoozed() == frozenset({(ADVANCE, 2026, 7)})
    assert PaymentReminderService.reminders_to_send(EVENING) == []


def test_snooze_rejects_unknown_kind(temp_db):
    with pytest.raises(ValueError):
        PaymentReminderService.snooze("bonus", 2026, 7, EVENING)

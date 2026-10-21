"""
Напоминания о вводе аванса и зарплаты (для Telegram-бота).

Дни выплат не настраиваются, а определяются по истории: самый частый день
выплаты за последний год и самый частый сдвиг между месяцем, за который
выплата, и месяцем, когда она пришла (аванс — в том же месяце, зарплата —
в следующем). Если работодатель сдвинет дату, расписание подстроится само.

В день выплаты и следующие дни (всего REPEAT_DAYS вечеров), если сумма
ещё не внесена, бот напоминает в SEND_FROM..SEND_UNTIL по МСК.

Время: «сегодня» и окно отправки — по МСК (расписание для человека),
даты выплат — календарные даты, между поясами не переводятся.
"""
from __future__ import annotations

import calendar
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable

from core.repositories.reminder_state_repository import ReminderStateRepository
from core.repositories.salary_repository import SalaryRepository
from core.services.settings_service import SettingsService
from core.utils.clock import MOSCOW_TZ, moscow_now

ADVANCE = "advance"
SALARY = "salary"
KINDS = (ADVANCE, SALARY)

DEFAULT_DAY = {ADVANCE: 28, SALARY: 14}  # пока истории мало
DEFAULT_LAG = {ADVANCE: 0, SALARY: 1}    # месяцев между «за какой» и «когда пришла»
HISTORY_DAYS = 365
REPEAT_DAYS = 5
SEND_FROM = time(19, 0)   # МСК
SEND_UNTIL = time(23, 0)  # МСК: после — не будить, напомним завтра


@dataclass(frozen=True)
class PaymentSchedule:
    kind: str
    day: int  # обычный день месяца, когда приходит выплата
    lag: int  # 0 — приходит в том же месяце, 1 — в следующем


@dataclass(frozen=True)
class Reminder:
    kind: str
    year: int       # месяц, за который выплата
    month: int
    due_date: date  # когда она обычно приходит
    evening: int    # 1 — в день выплаты, 2..REPEAT_DAYS — повторы


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _payment_date(record: Any, kind: str) -> date | None:
    value = getattr(record, f"{kind}_date", None)
    return value.date() if isinstance(value, datetime) else value


def _amount(record: Any, kind: str) -> float:
    return float(getattr(record, kind, 0) or 0)


class PaymentReminderService:
    """Расписание выплат по истории и напоминания, которые пора отправить."""

    @staticmethod
    def learn_schedule(records: Iterable[Any], today: date) -> dict[str, PaymentSchedule]:
        records = list(records)
        since = today - timedelta(days=HISTORY_DAYS)
        schedules = {}
        for kind in KINDS:
            paid = [
                (paid_on, record)
                for record in records
                if _amount(record, kind) > 0
                and (paid_on := _payment_date(record, kind)) is not None
                and since <= paid_on <= today
            ]
            if not paid:
                schedules[kind] = PaymentSchedule(kind, DEFAULT_DAY[kind], DEFAULT_LAG[kind])
                continue
            paid.sort(key=lambda item: item[0])
            days = Counter(paid_on.day for paid_on, _ in paid)
            lags = Counter(
                (paid_on.year * 12 + paid_on.month) - (record.year * 12 + record.month)
                for paid_on, record in paid
            )
            top = max(days.values())
            # При равенстве — день самой свежей выплаты
            day = next(paid_on.day for paid_on, _ in reversed(paid) if days[paid_on.day] == top)
            lag = max(0, min(2, lags.most_common(1)[0][0]))
            schedules[kind] = PaymentSchedule(kind, day, lag)
        return schedules

    @staticmethod
    def due_reminders(
        records: Iterable[Any],
        today: date,
        snoozed: frozenset[tuple[str, int, int]] = frozenset(),
    ) -> list[Reminder]:
        records = list(records)
        by_month = {(record.year, record.month): record for record in records}
        reminders = []
        for kind, schedule in PaymentReminderService.learn_schedule(records, today).items():
            # Окно повторов может начаться в прошлом месяце (выплата 28-го + 5 дней)
            for back in (1, 0):
                pay_year, pay_month = _shift_month(today.year, today.month, -back)
                last_day = calendar.monthrange(pay_year, pay_month)[1]
                due = date(pay_year, pay_month, min(schedule.day, last_day))
                evening = (today - due).days + 1
                if not 1 <= evening <= REPEAT_DAYS:
                    continue
                year, month = _shift_month(pay_year, pay_month, -schedule.lag)
                record = by_month.get((year, month))
                if record is not None and _amount(record, kind) > 0:
                    continue
                if (kind, year, month) in snoozed:
                    continue
                reminders.append(Reminder(kind, year, month, due, evening))
        return reminders

    @staticmethod
    def is_send_time(now: datetime) -> bool:
        local = now.astimezone(MOSCOW_TZ).time()
        return SEND_FROM <= local < SEND_UNTIL

    # --- С состоянием (БД) ------------------------------------------------------

    @staticmethod
    def enabled() -> bool:
        return SettingsService.get_setting("telegram_reminders") == "1"

    @classmethod
    def reminders_to_send(cls, now: datetime | None = None) -> list[Reminder]:
        """
        Напоминания, которые пора отправить сейчас.

        Пусто, если выключено в настройках, не вечер по МСК или сегодня уже
        отправляли (бот проверяет часто, отправка — раз в вечер).
        """
        now = now or moscow_now()
        today = now.astimezone(MOSCOW_TZ).date()
        if not cls.enabled() or not cls.is_send_time(now):
            return []
        if ReminderStateRepository.get_last_sent() == today:
            return []
        return cls.due_reminders(
            SalaryRepository.get_all(), today, ReminderStateRepository.get_snoozed()
        )

    @staticmethod
    def mark_sent(now: datetime | None = None) -> None:
        now = now or moscow_now()
        ReminderStateRepository.set_last_sent(now.astimezone(MOSCOW_TZ).date())

    @staticmethod
    def snooze(kind: str, year: int, month: int, now: datetime | None = None) -> None:
        if kind not in KINDS:
            raise ValueError(f"Неизвестный вид выплаты: {kind}")
        now = now or moscow_now()
        ReminderStateRepository.add_snoozed(kind, year, month, now.astimezone(MOSCOW_TZ).date())

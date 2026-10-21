"""
Годовой итог в Telegram: когда отправлять.

Не 1 января: зарплата за декабрь приходит в середине января, и итог
без неё был бы неполным. Итог за прошлый год отправляется в январе,
в вечернее окно уведомлений по МСК, когда декабрь закрыт (зарплата за
декабрь внесена) — либо с LATEST_DAY января, даже если декабрь так и
не внесён. Отправляется один раз за год; выключается той же настройкой,
что и напоминания о выплатах.
"""
from __future__ import annotations

from datetime import datetime

from core.repositories.reminder_state_repository import ReminderStateRepository
from core.repositories.salary_repository import SalaryRepository
from core.services.reminder_service import PaymentReminderService
from core.utils.clock import MOSCOW_TZ, moscow_now

LATEST_DAY = 25  # января: дальше ждать декабрь нет смысла


class AnnualReportService:
    """Решает, пора ли отправить годовой итог, и запоминает отправку."""

    @staticmethod
    def year_to_report(now: datetime | None = None) -> int | None:
        now = now or moscow_now()
        today = now.astimezone(MOSCOW_TZ).date()
        year = today.year - 1
        if today.month != 1 or not PaymentReminderService.enabled():
            return None
        if not PaymentReminderService.is_send_time(now):
            return None
        sent = ReminderStateRepository.get_annual_sent()
        if sent is not None and sent >= year:
            return None
        records = {record.month: record for record in SalaryRepository.get_by_year(year)}
        if not records:
            return None
        december = records.get(12)
        december_closed = december is not None and december.salary > 0
        return year if december_closed or today.day >= LATEST_DAY else None

    @staticmethod
    def mark_sent(year: int) -> None:
        ReminderStateRepository.set_annual_sent(year)

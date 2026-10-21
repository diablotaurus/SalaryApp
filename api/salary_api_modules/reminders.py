"""Напоминания Telegram-бота о вводе выплат."""
from __future__ import annotations

from dataclasses import asdict

from api.common import execute_with_default_error, success
from core.services.annual_report_service import AnnualReportService
from core.services.reminder_service import PaymentReminderService


def get_reminders_to_send() -> dict:
    def _action() -> dict:
        reminders = PaymentReminderService.reminders_to_send()
        return success([asdict(item) for item in reminders], count=len(reminders))

    return execute_with_default_error(_action, "Ошибка при подготовке напоминаний")


def mark_reminders_sent() -> dict:
    def _action() -> dict:
        PaymentReminderService.mark_sent()
        return success()

    return execute_with_default_error(_action, "Ошибка при сохранении отметки напоминаний")


def snooze_reminder(kind: str, year: int, month: int) -> dict:
    def _action() -> dict:
        PaymentReminderService.snooze(kind, year, month)
        return success()

    return execute_with_default_error(_action, "Ошибка при отключении напоминания")


def get_annual_report_year() -> dict:
    """Год, за который пора отправить годовой итог (data=None — пока не пора)."""
    return execute_with_default_error(
        lambda: success(AnnualReportService.year_to_report()),
        "Ошибка при проверке годового итога",
    )


def mark_annual_report_sent(year: int) -> dict:
    def _action() -> dict:
        AnnualReportService.mark_sent(year)
        return success()

    return execute_with_default_error(_action, "Ошибка при сохранении отметки годового итога")

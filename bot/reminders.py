"""
Напоминания о вводе аванса и зарплаты.

Бот раз в CHECK_INTERVAL_SECONDS спрашивает ядро, не пора ли напомнить
(когда и о чём — решает PaymentReminderService: вечер по МСК, раз в день,
дни выплат — по истории). Частая проверка, а не «сон до 19:00», переживает
сон компьютера и перезапуски бота.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BufferedInputFile

from api.salary_api import SalaryAPI
from bot.keyboards import salary as keyboards
from bot.presenters import charts
from bot.presenters.year_report import format_annual_report
from core.utils.dates import DateUtils

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 300

_PHRASES = {
    # (сегодня день выплаты, повтор)
    "advance": (
        "🔔 Сегодня обычно приходит аванс за {period} ({day}-го). Пришёл? Внесите сумму.",
        "🔔 Напоминаю: аванс за {period} ещё не внесён (обычно приходит {day}-го).",
    ),
    "salary": (
        "🔔 Сегодня обычно приходит зарплата за {period} ({day}-го). Пришла? Внесите сумму.",
        "🔔 Напоминаю: зарплата за {period} ещё не внесена (обычно приходит {day}-го).",
    ),
}


def format_reminder(reminder: dict[str, Any]) -> str:
    first, repeat = _PHRASES[reminder["kind"]]
    template = first if reminder["evening"] == 1 else repeat
    period = f"{DateUtils.get_month_name(reminder['month']).lower()} {reminder['year']}"
    return template.format(period=period, day=reminder["due_date"].day)


async def send_due_reminders(bot: Bot, user_ids: Iterable[int]) -> int:
    """Отправить напоминания, если пора. Возвращает число доставленных сообщений."""
    response = SalaryAPI.get_reminders_to_send()
    if not response.get("success"):
        logger.warning("Напоминания не подготовлены: %s", response.get("message"))
        return 0

    reminders = response.get("data") or []
    delivered = 0
    for reminder in reminders:
        markup = keyboards.reminder_keyboard(reminder["kind"], reminder["year"], reminder["month"])
        for user_id in user_ids:
            try:
                await bot.send_message(user_id, format_reminder(reminder), reply_markup=markup)
                delivered += 1
            except TelegramAPIError:
                logger.exception("Не удалось отправить напоминание пользователю %s", user_id)

    # Сегодняшний вечер закрыт, если напоминать не о чем или хоть что-то дошло.
    # Если не дошло ничего (нет сети) — повтор через CHECK_INTERVAL_SECONDS.
    if not reminders or delivered:
        SalaryAPI.mark_reminders_sent()
    if delivered:
        logger.info("Отправлено напоминаний: %s", delivered)
    return delivered


async def send_annual_report(bot: Bot, user_ids: Iterable[int]) -> int:
    """
    Годовой итог с графиком — один раз, в январе, когда закрыт декабрь
    (когда — решает AnnualReportService). Возвращает число доставленных.
    """
    due = SalaryAPI.get_annual_report_year()
    year = due.get("data") if due.get("success") else None
    if year is None:
        return 0
    years = SalaryAPI.get_all_grouped_by_year()
    if not years.get("success"):
        return 0
    data = years.get("data") or []
    caption = format_annual_report(data, year)
    png = await asyncio.to_thread(charts.year_chart, data, year)

    delivered = 0
    for user_id in user_ids:
        try:
            await bot.send_photo(user_id, BufferedInputFile(png, filename=f"salary_{year}.png"), caption=caption)
            delivered += 1
        except TelegramAPIError:
            logger.exception("Не удалось отправить годовой итог пользователю %s", user_id)
    if delivered:
        SalaryAPI.mark_annual_report_sent(year)
        logger.info("Отправлен годовой итог за %s", year)
    return delivered


async def run_reminders(bot: Bot, user_ids: Iterable[int]) -> None:
    """Фоновая задача бота: напоминания о выплатах и годовой итог."""
    user_ids = tuple(user_ids)
    while True:
        for job in (send_due_reminders, send_annual_report):
            try:
                await job(bot, user_ids)
            except Exception:
                logger.exception("Сбой фоновой задачи %s", job.__name__)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

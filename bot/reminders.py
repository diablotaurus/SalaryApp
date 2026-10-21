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

from api.salary_api import SalaryAPI
from bot.keyboards import salary as keyboards
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


async def run_reminders(bot: Bot, user_ids: Iterable[int]) -> None:
    """Фоновая задача бота: проверять, не пора ли напомнить."""
    user_ids = tuple(user_ids)
    while True:
        try:
            await send_due_reminders(bot, user_ids)
        except Exception:
            logger.exception("Сбой при отправке напоминаний")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

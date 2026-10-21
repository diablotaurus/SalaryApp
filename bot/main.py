"""Telegram bot process bootstrap."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_allowed_user_ids, load_bot_token, load_proxies
from bot.handlers import reports_router, salary_router
from bot.middlewares import BotAccessMiddleware
from bot.reminders import run_reminders
from core.config.settings import config
from core.database.migrations import apply_all_migrations
from core.utils.logging_setup import configure_file_logging


logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """Configure rotating file logging when the bot process starts."""
    configure_file_logging(config.logging.bot_log_file)


def _load_bot_token() -> str:
    """Backward-compatible wrapper around bot configuration."""
    return load_bot_token()


def _load_proxies() -> list[str]:
    """Backward-compatible wrapper around bot configuration."""
    return load_proxies()


async def _create_bot(token: str) -> Bot:
    """
    Создать бота с учётом прокси.

    Если задан(ы) прокси (TELEGRAM_PROXY, можно несколько через запятую —
    предпочтительный первым), выбираем первый отвечающий. Если сейчас не отвечает
    ни один — используем предпочтительный и ждём его восстановления (aiogram сам
    повторяет попытки). Прямое подключение — только если прокси не задан вовсе.

    ВАЖНО: на этом ПК Telegram доступен только через прокси, поэтому откат на прямое
    подключение исключён — он приводил к падению процесса и зацикленному перезапуску.
    """
    proxies = _load_proxies()
    if not proxies:
        logger.info("Telegram: прямое подключение (прокси не задан)")
        return Bot(token=token)

    # Пробуем прокси по приоритету; берём первый отвечающий.
    for proxy in proxies:
        bot = Bot(token=token, session=AiohttpSession(proxy=proxy))
        try:
            await asyncio.wait_for(bot.get_me(), timeout=8)
            logger.info("Telegram: подключение через прокси %s", proxy)
            return bot
        except Exception as exc:
            logger.warning("Прокси %s недоступен (%s), пробую следующий", proxy, exc)
            await bot.session.close()

    # Ни один прокси не ответил сейчас — используем предпочтительный и ждём,
    # пока он поднимется (НЕ уходим напрямую, чтобы не падать в цикле).
    primary = proxies[0]
    logger.warning("Ни один прокси не ответил; использую %s и жду восстановления", primary)
    return Bot(token=token, session=AiohttpSession(proxy=primary))


BOT_COMMANDS = [
    BotCommand(command="add", description="Внести аванс и зарплату"),
    BotCommand(command="current", description="Сводка за текущий год"),
    BotCommand(command="years", description="Итоги по годам"),
    BotCommand(command="reports", description="Графики, рекорды, Excel"),
    BotCommand(command="records", description="Рекорды"),
    BotCommand(command="cancel", description="Отменить ввод"),
    BotCommand(command="help", description="Справка и меню"),
]


async def _set_commands(bot: Bot) -> None:
    """Список команд для кнопки «Меню» в Telegram (сбой не мешает работе бота)."""
    try:
        await bot.set_my_commands(BOT_COMMANDS)
    except TelegramAPIError:
        logger.warning("Не удалось обновить список команд бота", exc_info=True)


async def main() -> None:
    """Validate configuration, initialize dependencies and start polling."""
    _setup_logging()
    allowed_user_ids = load_allowed_user_ids()
    apply_all_migrations()

    bot = await _create_bot(_load_bot_token())
    dispatcher = Dispatcher(storage=MemoryStorage())
    # Доступ проверяется и для сообщений, и для нажатий inline-кнопок
    access = BotAccessMiddleware(allowed_user_ids)
    dispatcher.message.outer_middleware(access)
    dispatcher.callback_query.outer_middleware(access)
    # Отчёты раньше ввода: кнопки «Этот год»/«По годам» работают и посреди ввода
    dispatcher.include_router(reports_router)
    dispatcher.include_router(salary_router)
    await _set_commands(bot)

    logger.info("Бот запущен")
    # Напоминания о вводе выплат — фоновая задача рядом с приёмом сообщений
    reminders_task = asyncio.create_task(run_reminders(bot, allowed_user_ids))
    try:
        await dispatcher.start_polling(bot)
    finally:
        reminders_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())

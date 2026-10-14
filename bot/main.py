"""Telegram bot process bootstrap."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_allowed_user_ids, load_bot_token, load_proxies
from bot.handlers import salary_router
from bot.middlewares import BotAccessMiddleware
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


async def main() -> None:
    """Validate configuration, initialize dependencies and start polling."""
    _setup_logging()
    allowed_user_ids = load_allowed_user_ids()
    apply_all_migrations()

    bot = await _create_bot(_load_bot_token())
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.message.outer_middleware(BotAccessMiddleware(allowed_user_ids))
    dispatcher.include_router(salary_router)

    logger.info("Бот запущен")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

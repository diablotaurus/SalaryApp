"""Telegram bot process bootstrap."""
from __future__ import annotations

import asyncio
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_allowed_user_ids, load_bot_token, load_proxy
from bot.handlers import salary_router
from bot.middlewares import BotAccessMiddleware
from core.config.settings import config
from core.database.migrations import apply_all_migrations


logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """Configure rotating file logging when the bot process starts."""
    handler = RotatingFileHandler(
        filename=str(config.logging.bot_log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(str(config.logging.format)))

    root = logging.getLogger()
    root.setLevel(getattr(logging, str(config.logging.level).upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)


def _load_bot_token() -> str:
    """Backward-compatible wrapper around bot configuration."""
    return load_bot_token()


def _load_proxy() -> Optional[str]:
    """Backward-compatible wrapper around bot configuration."""
    return load_proxy()


async def _create_bot(token: str) -> Bot:
    """Create a bot, falling back to a direct connection if proxy setup fails."""
    proxy = _load_proxy()
    if proxy:
        bot = Bot(token=token, session=AiohttpSession(proxy=proxy))
        try:
            await asyncio.wait_for(bot.get_me(), timeout=10)
            logger.info("Telegram: подключение через прокси %s", proxy)
            return bot
        except Exception as exc:
            logger.warning("Прокси %s недоступен (%s), подключаюсь напрямую", proxy, exc)
            await bot.session.close()

    return Bot(token=token)


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

"""Authorization middleware for the private Telegram bot."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)


class BotAccessMiddleware(BaseMiddleware):
    """Allow bot handlers only for explicitly configured Telegram users."""

    def __init__(self, allowed_user_ids: frozenset[int]):
        if not allowed_user_ids:
            raise ValueError("Telegram allowlist must not be empty")
        self._allowed_user_ids = allowed_user_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user") or getattr(event, "from_user", None)
        user_id = getattr(user, "id", None)
        if user_id in self._allowed_user_ids:
            return await handler(event, data)

        logger.warning("Отклонён доступ к Telegram-боту: user_id=%s", user_id)
        if isinstance(event, Message):
            await event.answer("Доступ к этому боту запрещён.")
        return None

"""Environment-backed configuration for the Telegram bot."""
from __future__ import annotations

import os
from pathlib import Path


ENV_FILE = Path(__file__).resolve().parent / ".env"


def _read_env_file() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_bot_token() -> str:
    values = _read_env_file()
    token = (
        os.getenv("SALARYAPP_BOT_TOKEN")
        or os.getenv("BOT_TOKEN")
        or values.get("SALARYAPP_BOT_TOKEN")
        or values.get("BOT_TOKEN")
        or values.get("API_TOKEN")
    )
    if not token or not token.strip():
        raise RuntimeError(
            "BOT_TOKEN не найден. Укажите его в bot/.env или переменной окружения."
        )
    return token.strip()


def load_proxy() -> str | None:
    values = _read_env_file()
    proxy = (
        os.getenv("SALARYAPP_TELEGRAM_PROXY")
        or os.getenv("TELEGRAM_PROXY")
        or values.get("SALARYAPP_TELEGRAM_PROXY")
        or values.get("TELEGRAM_PROXY")
    )
    return proxy.strip() if proxy and proxy.strip() else None


def load_allowed_user_ids() -> frozenset[int]:
    values = _read_env_file()
    raw_value = (
        os.getenv("SALARYAPP_BOT_ALLOWED_IDS")
        or os.getenv("BOT_ALLOWED_IDS")
        or values.get("SALARYAPP_BOT_ALLOWED_IDS")
        or values.get("BOT_ALLOWED_IDS")
        or ""
    )

    allowed_ids: set[int] = set()
    for item in raw_value.replace(";", ",").split(","):
        value = item.strip()
        if not value:
            continue
        try:
            user_id = int(value)
        except ValueError as exc:
            raise RuntimeError(
                f"Некорректный Telegram ID в BOT_ALLOWED_IDS: {value}"
            ) from exc
        if user_id <= 0:
            raise RuntimeError(f"Telegram ID должен быть положительным: {value}")
        allowed_ids.add(user_id)

    if not allowed_ids:
        raise RuntimeError(
            "BOT_ALLOWED_IDS не задан. Укажите разрешённые Telegram ID в bot/.env."
        )
    return frozenset(allowed_ids)

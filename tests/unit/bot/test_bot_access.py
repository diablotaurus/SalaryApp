import asyncio
from types import SimpleNamespace

import pytest

from bot.config import load_allowed_user_ids
from bot.middlewares import BotAccessMiddleware


def test_load_allowed_user_ids_from_environment(monkeypatch):
    monkeypatch.setenv("SALARYAPP_BOT_ALLOWED_IDS", "123, 456")

    assert load_allowed_user_ids() == frozenset({123, 456})


def test_empty_allowlist_fails_closed(monkeypatch, tmp_path):
    monkeypatch.delenv("SALARYAPP_BOT_ALLOWED_IDS", raising=False)
    monkeypatch.delenv("BOT_ALLOWED_IDS", raising=False)
    monkeypatch.delenv("ALLOWED_USER_IDS", raising=False)
    monkeypatch.setattr("bot.config.ENV_FILE", tmp_path / ".env")

    with pytest.raises(RuntimeError, match="BOT_ALLOWED_IDS"):
        load_allowed_user_ids()


@pytest.mark.parametrize("source", ["file", "environment"])
def test_legacy_allowed_ids(monkeypatch, tmp_path, source):
    for key in ("SALARYAPP_BOT_ALLOWED_IDS", "BOT_ALLOWED_IDS", "ALLOWED_USER_IDS"):
        monkeypatch.delenv(key, raising=False)
    env_file = tmp_path / ".env"
    monkeypatch.setattr("bot.config.ENV_FILE", env_file)
    if source == "file":
        env_file.write_text("ALLOWED_USER_IDS=92887913\n", encoding="utf-8")
    else:
        monkeypatch.setenv("ALLOWED_USER_IDS", "92887913")
    assert load_allowed_user_ids() == frozenset({92887913})


def test_canonical_allowed_ids_take_precedence(monkeypatch):
    monkeypatch.setenv("SALARYAPP_BOT_ALLOWED_IDS", "123")
    monkeypatch.setenv("ALLOWED_USER_IDS", "456")
    assert load_allowed_user_ids() == frozenset({123})


def test_middleware_allows_configured_user():
    middleware = BotAccessMiddleware(frozenset({123}))
    event = SimpleNamespace(from_user=SimpleNamespace(id=123))
    called = {"value": False}

    async def handler(_event, _data):
        called["value"] = True
        return "ok"

    result = asyncio.run(middleware(handler, event, {}))

    assert result == "ok"
    assert called["value"] is True


def test_middleware_blocks_unknown_user():
    middleware = BotAccessMiddleware(frozenset({123}))
    event = SimpleNamespace(from_user=SimpleNamespace(id=999))
    called = {"value": False}

    async def handler(_event, _data):
        called["value"] = True

    result = asyncio.run(middleware(handler, event, {}))

    assert result is None
    assert called["value"] is False

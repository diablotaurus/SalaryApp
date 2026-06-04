from __future__ import annotations

from typing import Any, Callable

from core.exceptions import RECOVERABLE_EXCEPTIONS, to_app_error

def execute_with_default_error(action: Callable[[], dict], message: str) -> dict:
    try:
        return action()
    except RECOVERABLE_EXCEPTIONS as exc:
        app_exc = to_app_error(exc, message)
        return {
            "success": False,
            "error": str(app_exc),
            "message": app_exc.user_message,
        }


def success(data: Any = None, **extra: Any) -> dict:
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return payload


def failure(message: str, error: str | None = None, **extra: Any) -> dict:
    payload = {"success": False, "message": message}
    if error is not None:
        payload["error"] = error
    payload.update(extra)
    return payload

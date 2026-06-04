"""
Shared API response helpers for web routes.
"""
from __future__ import annotations

from typing import Any

from core.exceptions import (
    BackupError,
    DataAccessError,
    ExportError,
    PresentationError,
    SalaryAppError,
    ServiceError,
    ValidationError,
)

RESPONSE_SCHEMA = {
    "success": bool,
    "data": object,
    "message": str,
    "error": (str, type(None)),
}

EXCEPTION_STATUS_MAP = {
    ValidationError: 400,
    ValueError: 400,
    TypeError: 400,
    KeyError: 400,
    PermissionError: 403,
    FileNotFoundError: 404,
    DataAccessError: 500,
    ExportError: 500,
    BackupError: 500,
    PresentationError: 500,
    ServiceError: 500,
    SalaryAppError: 500,
    RuntimeError: 500,
    OSError: 500,
}

PAYLOAD_STATUS_HINTS = {
    "forbidden": 403,
    "not found": 404,
    "required": 400,
    "invalid": 400,
}


def _normalize_payload(payload: Any, *, is_production: bool) -> dict:
    if not isinstance(payload, dict):
        payload = {"success": False, "message": "Invalid response format", "error": "invalid_payload"}

    success = bool(payload.get("success"))
    result = {
        "success": success,
        "data": payload.get("data", None),
        "message": str(payload.get("message", "OK" if success else "Request failed")),
        "error": payload.get("error", None),
    }

    if success:
        result["error"] = None
    elif is_production:
        result["error"] = None

    return result


def status_from_payload(payload: dict) -> int:
    if payload.get("success"):
        return 200

    message = str(payload.get("message", "")).lower()
    error = str(payload.get("error", "")).lower()
    signal = f"{message} {error}"
    for hint, status in PAYLOAD_STATUS_HINTS.items():
        if hint in signal:
            return status
    return 400


def payload_from_exception(exc: Exception, *, is_production: bool) -> tuple[dict, int]:
    status = 500
    for exc_type, mapped_status in EXCEPTION_STATUS_MAP.items():
        if isinstance(exc, exc_type):
            status = mapped_status
            break

    message = "Request failed"
    if isinstance(exc, SalaryAppError):
        message = exc.user_message
    elif status < 500:
        message = str(exc) or message

    payload = {
        "success": False,
        "data": None,
        "message": message,
        "error": None if is_production else str(exc),
    }
    return payload, status


def finalize_response(payload: Any, *, is_production: bool) -> tuple[dict, int]:
    normalized = _normalize_payload(payload, is_production=is_production)
    return normalized, status_from_payload(normalized)

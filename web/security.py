"""Central access control for SalaryApp web API."""
from __future__ import annotations

import hmac
import os

from flask import Flask, jsonify, request

from core.config.settings import config
from web.routes.response import finalize_response

LOOPBACK_ADDRESSES = {"127.0.0.1", "::1"}


def _configured_api_key() -> str:
    return (
        os.getenv("SALARYAPP_WEB_API_KEY") or config.app.web_api_key or ""
    ).strip()


def is_api_request_authorized() -> bool:
    if request.remote_addr in LOOPBACK_ADDRESSES:
        return True

    expected_key = _configured_api_key()
    provided_key = (request.headers.get("X-API-Key") or "").strip()
    return bool(expected_key and provided_key) and hmac.compare_digest(
        provided_key, expected_key
    )


def install_api_security(app: Flask) -> None:
    @app.before_request
    def require_api_access():
        if not request.path.startswith("/api/") or is_api_request_authorized():
            return None

        payload, status = finalize_response(
            {"success": False, "message": "Forbidden", "error": "forbidden"},
            is_production=config.app.is_production,
        )
        return jsonify(payload), status

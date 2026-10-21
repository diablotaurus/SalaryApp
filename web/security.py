"""Central access control for SalaryApp web API."""
from __future__ import annotations

import hmac
import os
from urllib.parse import urlsplit

from flask import Flask, jsonify, request

from core.config.settings import config
from web.routes.response import finalize_response

LOOPBACK_ADDRESSES = {"127.0.0.1", "::1"}
LOOPBACK_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}


def _configured_api_key() -> str:
    return (
        os.getenv("SALARYAPP_WEB_API_KEY") or config.app.web_api_key or ""
    ).strip()


def _host_header_is_loopback() -> bool:
    """
    Запрос адресован локальному серверу по имени (127.0.0.1, localhost, [::1]).

    Защита от DNS rebinding: чужой сайт может направить своё доменное имя
    на 127.0.0.1, и тогда запрос со страницы этого сайта придёт с локального
    адреса, но с чужим Host — такому запросу доверять без ключа нельзя.
    """
    hostname = urlsplit(f"//{request.host}").hostname or ""
    return hostname.lower() in LOOPBACK_HOSTNAMES


def is_api_request_authorized() -> bool:
    if request.remote_addr in LOOPBACK_ADDRESSES and _host_header_is_loopback():
        return True

    expected_key = _configured_api_key()
    provided_key = (request.headers.get("X-API-Key") or "").strip()
    return bool(expected_key and provided_key) and hmac.compare_digest(
        provided_key, expected_key
    )


def _rejection(message: str, error: str):
    payload, status = finalize_response(
        {"success": False, "message": message, "error": error},
        is_production=config.app.is_production,
    )
    return jsonify(payload), status


def install_api_security(app: Flask) -> None:
    @app.before_request
    def require_api_access():
        if not request.path.startswith("/api/"):
            return None
        if not is_api_request_authorized():
            return _rejection("Forbidden", "forbidden")
        # POST только с JSON: «простой» запрос (HTML-форма, text/plain) браузер
        # отправит с любого сайта без проверки CORS, а JSON — нет.
        if request.method == "POST" and not request.is_json:
            return _rejection("JSON body is required", "required")
        return None

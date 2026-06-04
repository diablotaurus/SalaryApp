"""
Settings API routes.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from api.settings_api import SettingsAPI
from core.config.settings import config
from web.routes.response import finalize_response, payload_from_exception

settings_bp = Blueprint("settings_api", __name__)


@settings_bp.route("/api/settings", methods=["GET"])
def get_settings():
    try:
        payload, status = finalize_response(SettingsAPI.get_settings(), is_production=config.app.is_production)
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@settings_bp.route("/api/settings/<key>", methods=["GET"])
def get_setting(key):
    try:
        payload, status = finalize_response(SettingsAPI.get_setting(key), is_production=config.app.is_production)
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@settings_bp.route("/api/settings/<key>", methods=["PUT"])
def update_setting(key):
    try:
        data = request.get_json(silent=True) or {}
        value = data.get("value", "")
        payload, status = finalize_response(
            SettingsAPI.set_setting(key, value),
            is_production=config.app.is_production,
        )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status

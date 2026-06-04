from web.app import create_app
from core.config.settings import config


def _client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_get_settings_route_uses_settings_api(monkeypatch):
    def fake_get_settings():
        return {"success": True, "data": {"currency": "rub"}}

    monkeypatch.setattr("api.settings_api.SettingsAPI.get_settings", fake_get_settings)

    response = _client().get("/api/settings")
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_update_setting_route_uses_set_setting(monkeypatch):
    called = {"value": None}

    def fake_set_setting(key, value):
        called["value"] = (key, value)
        return {"success": True, "data": {"key": key, "value": value}}

    monkeypatch.setattr("api.settings_api.SettingsAPI.set_setting", fake_set_setting)

    response = _client().put("/api/settings/theme", json={"value": "clam"})
    assert response.status_code == 200
    assert called["value"] == ("theme", "clam")


def test_update_setting_route_handles_non_json_body(monkeypatch):
    def fake_set_setting(key, value):
        return {"success": True, "data": {"key": key, "value": value}}

    monkeypatch.setattr("api.settings_api.SettingsAPI.set_setting", fake_set_setting)

    response = _client().put("/api/settings/theme", data="raw", content_type="text/plain")
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_settings_error_is_sanitized_in_production(monkeypatch):
    old_value = config.app.is_production
    config.app.is_production = True

    def fake_get_setting(_key, default=None):
        return {"success": False, "error": "traceback details", "message": "failed"}

    monkeypatch.setattr("api.settings_api.SettingsAPI.get_setting", fake_get_setting)

    response = _client().get("/api/settings/any")
    payload = response.get_json()

    config.app.is_production = old_value

    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["error"] is None

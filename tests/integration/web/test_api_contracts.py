from core.config.settings import config
from web.app import create_app


def _client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _assert_schema(payload: dict):
    assert set(payload.keys()) == {"success", "data", "message", "error"}


def test_delete_year_requires_api_key(monkeypatch):
    monkeypatch.setenv("SALARYAPP_WEB_API_KEY", "secret")
    response = _client().delete("/api/delete_year?year=2026")
    payload = response.get_json()

    assert response.status_code == 403
    _assert_schema(payload)
    assert payload["success"] is False


def test_delete_year_success_with_api_key(monkeypatch):
    monkeypatch.setenv("SALARYAPP_WEB_API_KEY", "secret")
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.delete_year",
        lambda year: {"success": True, "data": {"year": year}, "message": "ok"},
    )

    response = _client().delete("/api/delete_year?year=2026", headers={"X-API-Key": "secret"})
    payload = response.get_json()

    assert response.status_code == 200
    _assert_schema(payload)
    assert payload["success"] is True
    assert payload["data"]["year"] == 2026


def test_backup_failure_sanitized_in_production(monkeypatch):
    old_is_production = config.app.is_production
    config.app.is_production = True
    monkeypatch.setenv("SALARYAPP_WEB_API_KEY", "secret")
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.create_backup",
        lambda comment: {"success": False, "message": "backup failed", "error": "trace details"},
    )

    response = _client().post("/api/backup", json={"comment": "nightly"}, headers={"X-API-Key": "secret"})
    payload = response.get_json()

    config.app.is_production = old_is_production

    assert response.status_code == 400
    _assert_schema(payload)
    assert payload["success"] is False
    assert payload["error"] is None


def test_put_settings_success(monkeypatch):
    monkeypatch.setattr(
        "api.settings_api.SettingsAPI.set_setting",
        lambda key, value: {"success": True, "data": {"key": key, "value": value}, "message": "saved"},
    )

    response = _client().put("/api/settings/theme", json={"value": "clam"})
    payload = response.get_json()

    assert response.status_code == 200
    _assert_schema(payload)
    assert payload["success"] is True
    assert payload["data"]["key"] == "theme"


def test_put_settings_failure_sanitized_in_production(monkeypatch):
    old_is_production = config.app.is_production
    config.app.is_production = True
    monkeypatch.setattr(
        "api.settings_api.SettingsAPI.set_setting",
        lambda key, value: {"success": False, "message": "invalid", "error": "trace details"},
    )

    response = _client().put("/api/settings/theme", json={"value": "bad"})
    payload = response.get_json()

    config.app.is_production = old_is_production

    assert response.status_code == 400
    _assert_schema(payload)
    assert payload["success"] is False
    assert payload["error"] is None


def test_post_salary_missing_json_body(monkeypatch):
    monkeypatch.delenv("SALARYAPP_WEB_API_KEY", raising=False)
    response = _client().post("/api/salary", data="raw", content_type="text/plain")
    payload = response.get_json()

    assert response.status_code == 400
    _assert_schema(payload)
    assert payload["success"] is False


def test_post_salary_success(monkeypatch):
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.add_salary",
        lambda *args, **kwargs: {
            "success": True,
            "data": {"year": 2026, "month": 2, "advance": 10.0, "salary": 20.0},
            "message": "saved",
        },
    )

    response = _client().post(
        "/api/salary",
        json={"year": 2026, "month": 2, "advance": 10.0, "salary": 20.0},
    )
    payload = response.get_json()

    assert response.status_code == 200
    _assert_schema(payload)
    assert payload["success"] is True
    assert payload["error"] is None

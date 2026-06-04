from web.app import create_app


def _client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_delete_year_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("SALARYAPP_WEB_API_KEY", "secret")

    response = _client().delete("/api/delete_year?year=2024")
    assert response.status_code == 403
    assert response.get_json()["success"] is False


def test_delete_year_with_valid_api_key(monkeypatch):
    monkeypatch.setenv("SALARYAPP_WEB_API_KEY", "secret")

    called = {"year": None}

    def fake_delete_year(year):
        called["year"] = year
        return {"success": True, "message": "ok"}

    monkeypatch.setattr("api.salary_api.SalaryAPI.delete_year", fake_delete_year)

    response = _client().delete("/api/delete_year?year=2024", headers={"X-API-Key": "secret"})
    assert response.status_code == 200
    assert called["year"] == 2024


def test_create_backup_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("SALARYAPP_WEB_API_KEY", "secret")

    response = _client().post("/api/backup", json={"comment": "nightly"})
    assert response.status_code == 403
    assert response.get_json()["success"] is False


def test_add_salary_returns_400_when_json_body_is_missing(monkeypatch):
    called = {"ok": False}

    def fake_add_salary(*args, **kwargs):
        called["ok"] = True
        return {"success": True}

    monkeypatch.setattr("api.salary_api.SalaryAPI.add_salary", fake_add_salary)

    response = _client().post("/api/salary", data="raw", content_type="text/plain")
    assert response.status_code == 400
    assert called["ok"] is False

from web.app import create_app


def _client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_delete_year_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("SALARYAPP_WEB_API_KEY", "secret")

    response = _client().delete(
        "/api/delete_year?year=2024",
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )
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

    response = _client().post(
        "/api/backup",
        json={"comment": "nightly"},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )
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


def test_external_salary_write_requires_api_key(monkeypatch):
    monkeypatch.setenv("SALARYAPP_WEB_API_KEY", "secret")

    response = _client().post(
        "/api/salary",
        json={"year": 2026, "month": 1, "advance": 1, "salary": 2},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 403


def test_api_key_in_query_string_is_rejected(monkeypatch):
    monkeypatch.setenv("SALARYAPP_WEB_API_KEY", "secret")

    response = _client().get(
        "/api/salaries?api_key=secret",
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 403


def test_restore_backup_calls_api(monkeypatch):
    called = {}

    def fake_restore(reference):
        called["reference"] = reference
        return {"success": True, "message": "restored"}

    monkeypatch.setattr("api.salary_api.SalaryAPI.restore_backup", fake_restore)
    response = _client().post(
        "/api/backup/restore", json={"filename": "salary_backup_20260827.zip"}
    )

    assert response.status_code == 200
    assert called["reference"] == "salary_backup_20260827.zip"


def test_delete_backup_calls_api(monkeypatch):
    called = {}

    def fake_delete(reference):
        called["reference"] = reference
        return {"success": True, "message": "deleted"}

    monkeypatch.setattr("api.salary_api.SalaryAPI.delete_backup", fake_delete)
    response = _client().delete(
        "/api/backup", json={"filename": "salary_backup_20260827.zip"}
    )

    assert response.status_code == 200
    assert called["reference"] == "salary_backup_20260827.zip"


def test_unknown_api_route_returns_json_contract():
    response = _client().get("/api/does-not-exist")
    payload = response.get_json()

    assert response.status_code == 404
    assert set(payload) == {"success", "data", "message", "error"}

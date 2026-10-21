import pytest

from web.app import create_app


def _client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    monkeypatch.delenv("SALARYAPP_WEB_API_KEY", raising=False)
    monkeypatch.setattr("web.security.config.app.web_api_key", "")


@pytest.fixture
def years_api(monkeypatch):
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.get_years", lambda: {"success": True, "data": [2026]}
    )


@pytest.mark.parametrize(
    "base_url",
    ["http://localhost:5000", "http://127.0.0.1:5000", "http://[::1]:5000", "http://LOCALHOST"],
)
def test_local_browser_is_trusted(years_api, base_url):
    response = _client().get("/api/years", base_url=base_url)

    assert response.status_code == 200


def test_foreign_host_from_loopback_is_rejected(years_api):
    # DNS rebinding: чужой домен направлен на 127.0.0.1 — Host остаётся чужим.
    response = _client().get("/api/years", base_url="http://evil.example:5000")

    assert response.status_code == 403
    assert response.get_json()["success"] is False


def test_foreign_host_with_valid_api_key_is_allowed(years_api, monkeypatch):
    monkeypatch.setenv("SALARYAPP_WEB_API_KEY", "secret")

    response = _client().get(
        "/api/years", base_url="http://salary.lan:5000", headers={"X-API-Key": "secret"}
    )

    assert response.status_code == 200


def test_pages_are_not_affected_by_api_checks():
    response = _client().get("/", base_url="http://evil.example:5000")

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("data", "content_type"),
    [({"comment": "x"}, None), ("comment=x", "application/x-www-form-urlencoded"), ("x", "text/plain")],
)
def test_post_without_json_does_not_reach_action(monkeypatch, data, content_type):
    # HTML-форма или text/plain с чужого сайта отправляются без проверки CORS.
    called = []
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.create_backup", lambda comment="": called.append(comment)
    )

    kwargs = {"data": data}
    if content_type:
        kwargs["content_type"] = content_type
    response = _client().post("/api/backup", **kwargs)

    assert response.status_code == 400
    assert called == []


def test_post_with_json_reaches_action(monkeypatch):
    called = []
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.create_backup",
        lambda comment="": called.append(comment) or {"success": True, "data": {"filepath": "x"}},
    )

    response = _client().post("/api/backup", json={"comment": "nightly"})

    assert response.status_code == 200
    assert called == ["nightly"]


def test_web_export_is_sent_from_memory_and_removed_from_disk(monkeypatch, tmp_path):
    export_file = tmp_path / "salary_export_20261015_120000.csv"
    export_file.write_bytes(b"\xef\xbb\xbf\xd0\x93\xd0\xbe\xd0\xb4;...")
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.export_data",
        lambda fmt: {"success": True, "data": {"filepath": str(export_file), "format": fmt}},
    )

    response = _client().get("/api/export?format=csv")

    assert response.status_code == 200
    assert response.data.startswith(b"\xef\xbb\xbf")
    assert "salary_export_20261015_120000.csv" in response.headers["Content-Disposition"]
    assert not export_file.exists()  # копия данных не остаётся в exports/

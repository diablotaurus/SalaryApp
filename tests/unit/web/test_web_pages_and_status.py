import pytest

from core.config.settings import config
from web.app import create_app
from web.routes.response import finalize_response


def _client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.mark.parametrize("path", ["/", "/settings"])
def test_pages_show_real_app_version(monkeypatch, path):
    # Раньше в подвале и настройках были зашиты «v1.0» и «1.0.0»
    monkeypatch.setattr(config.app, "version", "9.8.7")

    html = _client().get(path).get_data(as_text=True)

    assert "9.8.7" in html
    assert "v1.0<" not in html and ">1.0.0<" not in html


@pytest.mark.parametrize("is_production", [False, True])
def test_not_found_keeps_404_in_production(is_production):
    # В production поле error скрывается — раньше вместе с ним терялся и статус 404
    payload, status = finalize_response(
        {"success": False, "message": "Резервная копия не найдена", "error": "not found"},
        is_production=is_production,
    )

    assert status == 404
    assert (payload["error"] is None) is is_production


def test_empty_month_is_404_not_400(temp_db):
    response = _client().get("/api/salary/2026/10")

    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_filled_month_is_returned(temp_db):
    client = _client()
    client.post("/api/salary", json={"year": 2026, "month": 10, "advance": 1, "salary": 2})

    response = client.get("/api/salary/2026/10")

    assert response.status_code == 200
    assert response.get_json()["data"]["total"] == 3


def test_forecast_endpoint(monkeypatch):
    called = {}

    def fake_forecast(year):
        called["year"] = year
        return {"success": True, "data": {"year": year, "forecast": 1289512.4}}

    monkeypatch.setattr("api.salary_api.SalaryAPI.forecast_year", fake_forecast)
    monkeypatch.setattr("web.routes.salaries.DateUtils.get_current_period", lambda: (2026, 10))

    response = _client().get("/api/forecast")

    assert response.status_code == 200
    assert called["year"] == 2026
    assert response.get_json()["data"]["forecast"] == 1289512.4

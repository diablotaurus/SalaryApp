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


def test_web_form_saves_and_clears_note(temp_db):
    client = _client()
    base = {"year": 2026, "month": 10, "advance": 1, "salary": 2}

    client.post("/api/salary", json={**base, "note": "отпуск"})
    assert client.get("/api/salary/2026/10").get_json()["data"]["note"] == "отпуск"

    client.post("/api/salary", json={**base, "note": ""})  # поле формы стёрли
    assert client.get("/api/salary/2026/10").get_json()["data"]["note"] == ""


def test_index_page_has_note_field():
    assert 'id="note"' in _client().get("/").get_data(as_text=True)


def test_extras_endpoints_add_list_delete(temp_db):
    client = _client()
    client.post("/api/salary", json={"year": 2026, "month": 8, "advance": 100, "salary": 200})

    added = client.post("/api/extras", json={
        "year": 2026, "month": 8, "kind": "vacation", "amount": 35000, "paid_date": "10.08.2026", "comment": "",
    })
    assert added.status_code == 200
    payment_id = added.get_json()["data"]["id"]

    listed = client.get("/api/extras?year=2026&month=8").get_json()["data"]
    assert [(p["kind_name"], p["amount"]) for p in listed] == [("Отпускные", 35000.0)]
    assert client.get("/api/salary/2026/8").get_json()["data"]["total"] == 35300.0

    assert client.delete(f"/api/extras/{payment_id}").status_code == 200
    assert client.delete(f"/api/extras/{payment_id}").status_code == 404
    assert client.get("/api/extras?year=2026&month=8").get_json()["data"] == []


def test_invalid_extra_is_400(temp_db):
    response = _client().post("/api/extras", json={"year": 2026, "month": 8, "kind": "bonus", "amount": 0})

    assert response.status_code == 400
    assert "больше нуля" in response.get_json()["message"]


def test_index_lists_extra_kinds():
    html = _client().get("/").get_data(as_text=True)

    assert 'id="extrasList"' in html
    assert '<option value="vacation">Отпускные</option>' in html

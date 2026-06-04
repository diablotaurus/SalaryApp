from core.models.salary import Salary
from api.salary_api import SalaryAPI


def test_salary_api_add_salary_success(monkeypatch):
    def fake_add_salary(*args, **kwargs):
        return Salary(id=1, year=2025, month=6, advance=10000.0, salary=20000.0)

    monkeypatch.setattr("api.salary_api.SalaryService.add_salary", fake_add_salary)

    response = SalaryAPI.add_salary(2025, 6, 10000.0, 20000.0, "10.06.2025", "25.06.2025")

    assert response["success"] is True
    assert response["data"]["year"] == 2025
    assert response["data"]["month"] == 6
    assert response["data"]["advance"] == 10000.0
    assert response["data"]["salary"] == 20000.0


def test_salary_api_add_salary_value_error(monkeypatch):
    def fake_add_salary(*args, **kwargs):
        raise ValueError("Неверный формат даты")

    monkeypatch.setattr("api.salary_api.SalaryService.add_salary", fake_add_salary)

    response = SalaryAPI.add_salary(2025, 6, 10000.0, 20000.0, "bad-date", None)

    assert response["success"] is False
    assert "Неверный формат даты" in response["message"]


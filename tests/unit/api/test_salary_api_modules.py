from api.salary_api_modules import commands, queries
from core.models.salary import Salary


def test_queries_get_salary_not_found(monkeypatch):
    monkeypatch.setattr("api.salary_api_modules.queries.SalaryService.get_salary", lambda y, m: None)

    response = queries.get_salary(2026, 2)

    assert response["success"] is False
    assert "не найдены" in response["message"]


def test_queries_get_all_salaries_success(monkeypatch):
    rows = [Salary(id=1, year=2026, month=1, advance=100.0, salary=200.0)]
    monkeypatch.setattr("api.salary_api_modules.queries.SalaryService.get_all_salaries", lambda: rows)

    response = queries.get_all_salaries()

    assert response["success"] is True
    assert response["count"] == 1
    assert response["data"][0]["year"] == 2026


def test_commands_delete_year_failure(monkeypatch):
    monkeypatch.setattr("api.salary_api_modules.commands.SalaryService.delete_year", lambda year: False)

    response = commands.delete_year(2024)

    assert response["success"] is False
    assert "Не удалось удалить" in response["message"]

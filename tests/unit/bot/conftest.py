import pytest


@pytest.fixture(autouse=True)
def no_month_comparison(monkeypatch):
    """
    Сохранение месяца в боте сравнивает его со средним (обращение к БД).
    По умолчанию сравнивать не с чем — тесты бота не трогают настоящую базу;
    тест сравнения подменяет ответ сам.
    """
    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.compare_with_recent_average",
        lambda year, month: {"success": True, "data": None},
    )

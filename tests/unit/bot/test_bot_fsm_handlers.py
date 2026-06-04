import asyncio

from bot.main import (
    SalaryStates,
    _format_year_table,
    _format_current_year_table,
    _parse_optional_date,
    cmd_current,
    cmd_year_stats,
    process_advance,
    process_salary_date,
    process_year,
)


class FakeMessage:
    def __init__(self, text: str):
        self.text = text
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class FakeState:
    def __init__(self, data=None):
        self.data = data or {}
        self.current_state = None
        self.cleared = False

    async def set_state(self, state):
        self.current_state = state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.cleared = True


def test_parse_optional_date_special_values():
    assert _parse_optional_date("-") is None
    assert _parse_optional_date("нет") is None
    assert _parse_optional_date("skip") is None
    assert _parse_optional_date("пропустить") is None
    assert _parse_optional_date("01.01.2025") == "01.01.2025"


def test_process_year_valid():
    msg = FakeMessage("2025")
    state = FakeState()

    asyncio.run(process_year(msg, state))

    assert state.data["year"] == 2025
    assert state.current_state == SalaryStates.waiting_for_month
    assert "Введите номер месяца (1-12):" in msg.answers[-1][0]


def test_process_year_invalid_text():
    msg = FakeMessage("abcd")
    state = FakeState()

    asyncio.run(process_year(msg, state))

    assert state.current_state is None
    assert state.data == {}
    assert "Введите число (год):" in msg.answers[-1][0]


def test_process_advance_negative_value():
    msg = FakeMessage("-1")
    state = FakeState()

    asyncio.run(process_advance(msg, state))

    assert "advance" not in state.data
    assert state.current_state is None
    assert "Сумма не может быть отрицательной" in msg.answers[-1][0]


def test_process_salary_date_success(monkeypatch):
    msg = FakeMessage("-")
    state = FakeState(
        {
            "year": 2025,
            "month": 8,
            "advance": 10000.0,
            "salary": 20000.0,
            "advance_date": None,
        }
    )
    called = {}

    def fake_add_salary(year, month, advance, salary, advance_date, salary_date):
        called["args"] = (year, month, advance, salary, advance_date, salary_date)
        return {
            "success": True,
            "data": {
                "year": 2025,
                "month_name": "Август",
                "advance": 10000.0,
                "salary": 20000.0,
            },
        }

    monkeypatch.setattr("bot.main.SalaryAPI.add_salary", fake_add_salary)

    asyncio.run(process_salary_date(msg, state))

    assert called["args"] == (2025, 8, 10000.0, 20000.0, None, None)
    assert state.cleared is True
    assert "Запись успешно сохранена" in msg.answers[-1][0]


def test_process_salary_date_api_error(monkeypatch):
    msg = FakeMessage("15.08.2025")
    state = FakeState(
        {
            "year": 2025,
            "month": 8,
            "advance": 10000.0,
            "salary": 20000.0,
            "advance_date": "10.08.2025",
        }
    )

    def fake_add_salary(*args, **kwargs):
        return {"success": False, "message": "Ошибка валидации"}

    monkeypatch.setattr("bot.main.SalaryAPI.add_salary", fake_add_salary)

    asyncio.run(process_salary_date(msg, state))

    assert state.cleared is True
    assert "Ошибка валидации" in msg.answers[-1][0]


def test_format_current_year_table_compact_layout(monkeypatch):
    monkeypatch.setattr(
        "bot.main.SalaryAPI.get_salaries_by_year",
        lambda year: {
            "success": True,
            "data": [
                {
                    "month": 1,
                    "month_name": "Январь",
                    "advance": 20783.87,
                    "advance_date": "28.01.2026",
                    "salary": 84562.16,
                    "salary_date": "13.02.2026",
                    "total": 105346.03,
                },
                {
                    "month": 2,
                    "month_name": "Февраль",
                    "advance": 41021.06,
                    "advance_date": "27.02.2026",
                    "salary": 68673.96,
                    "salary_date": "13.03.2026",
                    "total": 109695.02,
                },
            ],
        },
    )

    result = _format_current_year_table()

    assert "Статистика за" in result
    assert "Январь" in result
    assert "  Аванс: 20 783.87  •  28.01.2026" in result
    assert "  Зарплата: 84 562.16  •  13.02.2026" in result
    assert "  Итого: 105 346.03" in result
    assert "Итого за год: 215 041.05" in result
    assert "<pre>" not in result


def test_cmd_current_sends_plain_text(monkeypatch):
    async def fake_answer(text, **kwargs):
        msg.answers.append((text, kwargs))

    msg = FakeMessage("/current")
    msg.answer = fake_answer

    monkeypatch.setattr("bot.main._format_current_year_table", lambda: "Тестовый вывод")

    asyncio.run(cmd_current(msg))

    assert msg.answers == [("Тестовый вывод", {})]


def test_format_year_table_uses_requested_year(monkeypatch):
    called = {}

    def fake_get_salaries_by_year(year):
        called["year"] = year
        return {
            "success": True,
            "data": [
                {
                    "month": 1,
                    "month_name": "Январь",
                    "advance": 10000.0,
                    "advance_date": "25.01.2025",
                    "salary": 50000.0,
                    "salary_date": "10.02.2025",
                    "total": 60000.0,
                }
            ],
        }

    monkeypatch.setattr("bot.main.SalaryAPI.get_salaries_by_year", fake_get_salaries_by_year)

    result = _format_year_table(2025)

    assert called["year"] == 2025
    assert "Статистика за 2025 год" in result
    assert "Итого за год: 60 000.00" in result


def test_cmd_year_stats_sends_plain_text(monkeypatch):
    async def fake_answer(text, **kwargs):
        msg.answers.append((text, kwargs))

    msg = FakeMessage("/2025")
    msg.answer = fake_answer

    monkeypatch.setattr("bot.main._format_year_table", lambda year: f"Статистика за {year} год")

    asyncio.run(cmd_year_stats(msg))

    assert msg.answers == [("Статистика за 2025 год", {})]

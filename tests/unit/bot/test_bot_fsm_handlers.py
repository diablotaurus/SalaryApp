import asyncio

import pytest

from bot.handlers.salary import (
    SalaryStates,
    _format_year_table,
    _format_current_year_table,
    _is_cancel_text,
    _parse_optional_date,
    cmd_cancel,
    cmd_current,
    cmd_year_stats,
    process_advance,
    process_advance_date,
    process_month,
    process_non_text,
    process_salary,
    process_salary_date,
    process_year,
    router,
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

    async def get_state(self):
        return self.current_state

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


@pytest.mark.parametrize(
    ("text", "expected"),
    [("87 432,71", 87432.71), ("87 432,71", 87432.71), ("1000", 1000.0), ("12.345,67", 12345.67)],
)
def test_process_advance_understands_amounts_like_desktop(text, expected):
    # Суммы из банковских приложений — с пробелами (в т.ч. неразрывными) и запятой
    msg = FakeMessage(text)
    state = FakeState()

    asyncio.run(process_advance(msg, state))

    assert state.data["advance"] == expected
    assert state.current_state == SalaryStates.waiting_for_advance_date


@pytest.mark.parametrize("text", ["nan", "1e5", "87432,7l", "87.432.71", "inf"])
def test_process_salary_rejects_ambiguous_amount_on_its_step(text):
    # Раньше «nan» и «1e5» проходили шаг (float) и падали лишь при сохранении,
    # и весь введённый месяц терялся
    msg = FakeMessage(text)
    state = FakeState({"year": 2026, "month": 3, "advance": 1.0, "advance_date": None})

    asyncio.run(process_salary(msg, state))

    assert "salary" not in state.data
    assert state.current_state is None
    assert state.cleared is False
    assert "ожидается число" in msg.answers[-1][0]
    assert "Введите зарплату" in msg.answers[-1][0]


def test_saved_message_uses_russian_amount_format(monkeypatch):
    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.add_salary",
        lambda *args, **kwargs: {
            "success": True,
            "data": {"year": 2026, "month": 3, "month_name": "Март", "advance": 87432.71, "salary": 1000.0},
        },
    )
    msg = FakeMessage("-")
    state = FakeState({"year": 2026, "month": 3, "advance": 87432.71, "salary": 1000.0, "advance_date": None})

    asyncio.run(process_salary_date(msg, state))

    assert "87 432,71 руб." in msg.answers[-1][0]
    assert "88 432,71 руб." in msg.answers[-1][0]


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

    monkeypatch.setattr("bot.handlers.salary.SalaryAPI.add_salary", fake_add_salary)

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

    monkeypatch.setattr("bot.handlers.salary.SalaryAPI.add_salary", fake_add_salary)

    asyncio.run(process_salary_date(msg, state))

    assert state.cleared is True
    assert "Ошибка валидации" in msg.answers[-1][0]


def test_format_current_year_table_compact_layout(monkeypatch):
    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.get_salaries_by_year",
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
    assert "  Аванс: 20 783,87  •  28.01.2026" in result
    assert "  Зарплата: 84 562,16  •  13.02.2026" in result
    assert "  Итого: 105 346,03" in result
    assert "Итого за год: 215 041,05" in result
    assert "<pre>" not in result


def test_cmd_current_sends_plain_text(monkeypatch):
    async def fake_answer(text, **kwargs):
        msg.answers.append((text, kwargs))

    msg = FakeMessage("/current")
    msg.answer = fake_answer

    monkeypatch.setattr("bot.handlers.salary._format_current_year_table", lambda: "Тестовый вывод")

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

    monkeypatch.setattr("bot.handlers.salary.SalaryAPI.get_salaries_by_year", fake_get_salaries_by_year)

    result = _format_year_table(2025)

    assert called["year"] == 2025
    assert "Статистика за 2025 год" in result
    assert "Итого за год: 60 000,00" in result


def test_cmd_year_stats_sends_plain_text(monkeypatch):
    async def fake_answer(text, **kwargs):
        msg.answers.append((text, kwargs))

    msg = FakeMessage("/2025")
    msg.answer = fake_answer

    monkeypatch.setattr("bot.handlers.salary._format_year_table", lambda year: f"Статистика за {year} год")

    asyncio.run(cmd_year_stats(msg))

    assert msg.answers == [("Статистика за 2025 год", {})]


def test_cancel_clears_started_input():
    msg = FakeMessage("/cancel")
    state = FakeState({"year": 2026})
    state.current_state = SalaryStates.waiting_for_advance

    asyncio.run(cmd_cancel(msg, state))

    assert state.cleared is True
    assert "отменён" in msg.answers[-1][0]


def test_cancel_without_started_input():
    msg = FakeMessage("/cancel")
    state = FakeState()

    asyncio.run(cmd_cancel(msg, state))

    assert state.cleared is False
    assert "нечего отменять" in msg.answers[-1][0]


def test_cancel_words_are_recognized():
    assert _is_cancel_text(FakeMessage(" Отмена "))
    assert not _is_cancel_text(FakeMessage("1000"))
    assert not _is_cancel_text(FakeMessage(None))


def test_month_with_existing_data_shows_warning(monkeypatch):
    msg = FakeMessage("3")
    state = FakeState({"year": 2026})
    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.get_salary",
        lambda year, month: {
            "success": True,
            "data": {
                "year": year, "month_name": "Март",
                "advance": 31503.56, "salary": 76380.77,
                "advance_date": "27.03.2026", "salary_date": "14.04.2026",
            },
        },
    )

    asyncio.run(process_month(msg, state))

    warning = msg.answers[0][0]
    assert "За Март 2026 уже есть данные" in warning
    assert "31 503,56" in warning and "14.04.2026" in warning
    assert msg.answers[-1][0] == "Введите сумму аванса:"
    assert state.current_state == SalaryStates.waiting_for_advance


def test_month_without_data_has_no_warning(monkeypatch):
    msg = FakeMessage("3")
    state = FakeState({"year": 2026})
    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.get_salary",
        lambda year, month: {"success": False, "message": "не найдены"},
    )

    asyncio.run(process_month(msg, state))

    assert [answer[0] for answer in msg.answers] == ["Введите сумму аванса:"]


def test_invalid_advance_date_is_asked_again():
    # Раньше ошибка даты обнаруживалась только при сохранении, и ввод терялся.
    msg = FakeMessage("31.02.2026")
    state = FakeState({"year": 2026, "month": 2, "advance": 1000.0})
    state.current_state = SalaryStates.waiting_for_advance_date

    asyncio.run(process_advance_date(msg, state))

    assert state.current_state == SalaryStates.waiting_for_advance_date
    assert "advance_date" not in state.data
    assert "ДД.ММ.ГГГГ" in msg.answers[-1][0]


def test_advance_date_is_normalized():
    msg = FakeMessage("05032026")
    state = FakeState({"year": 2026, "month": 3, "advance": 1000.0})

    asyncio.run(process_advance_date(msg, state))

    assert state.data["advance_date"] == "05.03.2026"
    assert state.current_state == SalaryStates.waiting_for_salary


def test_invalid_salary_date_keeps_input(monkeypatch):
    msg = FakeMessage("99.99.2026")
    state = FakeState({"year": 2026, "month": 3, "advance": 1.0, "salary": 2.0, "advance_date": None})
    called = []
    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.add_salary", lambda *args: called.append(args)
    )

    asyncio.run(process_salary_date(msg, state))

    assert called == []
    assert state.cleared is False
    assert "ДД.ММ.ГГГГ" in msg.answers[-1][0]


def test_non_text_message_is_answered():
    msg = FakeMessage(None)

    asyncio.run(process_non_text(msg))

    assert "текстом" in msg.answers[-1][0]


def test_handler_registration_order():
    callbacks = [handler.callback for handler in router.message.handlers]
    first_step = callbacks.index(process_year)
    # Отмена должна срабатывать раньше шагов ввода, иначе «/cancel» станет ответом шага
    assert max(i for i, cb in enumerate(callbacks) if cb is cmd_cancel) < first_step
    # Ответ на нетекстовые сообщения — последним, после всех шагов
    assert callbacks[-1] is process_non_text


def _route(text, state=None):
    """Какой обработчик выберет роутер (настоящие фильтры aiogram, без сети)."""
    from datetime import datetime as _dt

    from aiogram.types import Chat, Message, User

    message = Message(
        message_id=1,
        date=_dt.now(),
        chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="u"),
        text=text,
    )

    async def _find():
        for handler in router.message.handlers:
            matched, _ = await handler.check(
                message, raw_state=state.state if state else None, bot=None
            )
            if matched:
                return handler.callback
        return None

    return asyncio.run(_find())


def test_routing_cancel_during_amount_input():
    assert _route("/cancel", SalaryStates.waiting_for_advance) is cmd_cancel
    assert _route("Отмена", SalaryStates.waiting_for_salary_date) is cmd_cancel


def test_routing_cancel_word_outside_input_is_not_a_command():
    assert _route("отмена") is None
    assert _route("/cancel") is cmd_cancel  # команда отвечает «нечего отменять»


def test_routing_regular_answers_and_non_text():
    assert _route("1000", SalaryStates.waiting_for_advance) is process_advance
    assert _route("2026", SalaryStates.waiting_for_year) is process_year
    assert _route(None, SalaryStates.waiting_for_advance) is process_non_text  # стикер, фото

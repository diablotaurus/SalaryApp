import asyncio
from datetime import date, datetime, timezone

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText
from aiogram.types import CallbackQuery, User

from bot.handlers.salary import (
    SalaryStates,
    cancel_by_button,
    choose_advance_date,
    choose_month,
    choose_period,
    choose_salary_date,
    cmd_add,
    router,
    stale_button,
)
from bot.keyboards import salary as keyboards
from bot.middlewares import BotAccessMiddleware


class FakeMessage:
    def __init__(self, text="", edit_error=None):
        self.text = text
        self.answers = []
        self.edited = []
        self._edit_error = edit_error

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))

    async def edit_text(self, text, **kwargs):
        if self._edit_error:
            raise self._edit_error
        self.edited.append(text)


class FakeCallback:
    def __init__(self, data, message=None):
        self.data = data
        self.message = message or FakeMessage("За какой месяц вносим данные?")
        self.answered = []

    async def answer(self, text=None, **kwargs):
        self.answered.append(text)


class FakeState:
    def __init__(self, data=None, current_state=None):
        self.data = data or {}
        self.current_state = current_state
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
        self.current_state = None


def _buttons(markup):
    return [(button.text, button.callback_data) for row in markup.inline_keyboard for button in row]


@pytest.fixture
def no_existing_month(monkeypatch):
    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.get_salary", lambda year, month: {"success": False}
    )


# --- Клавиатуры ------------------------------------------------------------------


def test_period_keyboard_offers_current_and_previous_month():
    # В январе прошлый месяц — декабрь предыдущего года
    assert _buttons(keyboards.period_keyboard(2026, 1)) == [
        ("Январь 2026", "period:2026:1"),
        ("Декабрь 2025", "period:2025:12"),
        ("Отмена", "cancel"),
    ]


def test_months_keyboard_has_all_months_and_cancel():
    buttons = _buttons(keyboards.months_keyboard())

    assert [data for _, data in buttons[:12]] == [f"month:{m}" for m in range(1, 13)]
    assert buttons[0][0] == "Янв" and buttons[-1] == ("Отмена", "cancel")


def test_callback_data_round_trip():
    assert keyboards.parse_period("period:2025:12") == (2025, 12)
    assert keyboards.parse_month("month:7") == 7


# --- Шаги по кнопкам -------------------------------------------------------------


def test_add_offers_current_moscow_month(monkeypatch):
    # 31.12 21:30 UTC — в Москве уже январь следующего года
    monkeypatch.setattr(
        "core.utils.clock.utc_now", lambda: datetime(2026, 12, 31, 21, 30, tzinfo=timezone.utc)
    )
    msg, state = FakeMessage("/add"), FakeState()

    asyncio.run(cmd_add(msg, state))

    assert state.current_state == SalaryStates.waiting_for_year
    assert _buttons(msg.answers[-1][1]["reply_markup"])[0] == ("Январь 2027", "period:2027:1")


def test_period_button_starts_month_and_shows_choice(no_existing_month):
    callback = FakeCallback("period:2026:10")
    state = FakeState(current_state=SalaryStates.waiting_for_year)

    asyncio.run(choose_period(callback, state))

    assert state.data == {"year": 2026, "month": 10}
    assert state.current_state == SalaryStates.waiting_for_advance
    assert callback.message.edited == ["За какой месяц вносим данные?\n➜ Октябрь 2026"]
    assert callback.message.answers[-1][0] == "Введите сумму аванса:"
    assert callback.answered == [None]  # «часики» на кнопке сняты


def test_period_button_warns_about_filled_month(monkeypatch):
    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.get_salary",
        lambda year, month: {"success": True, "data": {
            "year": year, "month_name": "Октябрь", "advance": 1.0, "salary": 2.0,
            "advance_date": "", "salary_date": "",
        }},
    )
    callback = FakeCallback("period:2026:10")

    asyncio.run(choose_period(callback, FakeState(current_state=SalaryStates.waiting_for_year)))

    assert "уже есть данные" in callback.message.answers[0][0]


def test_month_button_after_typed_year(no_existing_month):
    callback = FakeCallback("month:3", FakeMessage("Выберите месяц"))
    state = FakeState({"year": 2024}, SalaryStates.waiting_for_month)

    asyncio.run(choose_month(callback, state))

    assert state.data == {"year": 2024, "month": 3}
    assert callback.message.edited == ["Выберите месяц\n➜ Март"]


def test_today_button_uses_moscow_date(monkeypatch):
    monkeypatch.setattr("bot.handlers.salary.moscow_today", lambda: date(2026, 10, 21))
    callback = FakeCallback(keyboards.DATE_TODAY, FakeMessage("Введите дату аванса"))
    state = FakeState({"advance": 1.0}, SalaryStates.waiting_for_advance_date)

    asyncio.run(choose_advance_date(callback, state))

    assert state.data["advance_date"] == "21.10.2026"
    assert state.current_state == SalaryStates.waiting_for_salary
    assert callback.message.edited == ["Введите дату аванса\n➜ 21.10.2026"]


def test_skip_button_saves_month_without_salary_date(monkeypatch):
    saved = {}

    def fake_add(*args):
        saved["args"] = args
        return {"success": True, "data": {
            "year": 2026, "month_name": "Октябрь", "advance": 1.0, "salary": 2.0,
        }}

    monkeypatch.setattr("bot.handlers.salary.SalaryAPI.add_salary", fake_add)
    callback = FakeCallback(keyboards.DATE_SKIP, FakeMessage("Введите дату зарплаты"))
    state = FakeState(
        {"year": 2026, "month": 10, "advance": 1.0, "salary": 2.0, "advance_date": "28.10.2026"},
        SalaryStates.waiting_for_salary_date,
    )

    asyncio.run(choose_salary_date(callback, state))

    assert saved["args"] == (2026, 10, 1.0, 2.0, "28.10.2026", None)
    assert state.cleared is True
    assert "Запись успешно сохранена" in callback.message.answers[-1][0]
    assert callback.message.edited == ["Введите дату зарплаты\n➜ без даты"]


def test_cancel_button_clears_input():
    callback = FakeCallback(keyboards.CANCEL)
    state = FakeState({"year": 2026}, SalaryStates.waiting_for_month)

    asyncio.run(cancel_by_button(callback, state))

    assert state.cleared is True
    assert callback.message.answers[-1][0] == "Ввод отменён, данные не сохранены."


def test_old_message_that_cannot_be_edited_does_not_break_step(no_existing_month):
    error = TelegramBadRequest(method=EditMessageText(text="x"), message="message can't be edited")
    callback = FakeCallback("period:2026:10", FakeMessage("старое", edit_error=error))
    state = FakeState(current_state=SalaryStates.waiting_for_year)

    asyncio.run(choose_period(callback, state))

    assert state.current_state == SalaryStates.waiting_for_advance


def test_stale_button_only_answers():
    callback = FakeCallback("period:2026:10")

    asyncio.run(stale_button(callback))

    assert "неактуальна" in callback.answered[0]
    assert callback.message.answers == []


# --- Маршрутизация нажатий (настоящие фильтры aiogram) ------------------------------


def _route(data, state=None):
    callback = CallbackQuery(
        id="1",
        from_user=User(id=1, is_bot=False, first_name="u"),
        chat_instance="c",
        data=data,
    )

    async def _find():
        for handler in router.callback_query.handlers:
            matched, _ = await handler.check(callback, raw_state=state.state if state else None, bot=None)
            if matched:
                return handler.callback
        return None

    return asyncio.run(_find())


def test_routing_buttons_work_only_on_their_step():
    assert _route("period:2026:10", SalaryStates.waiting_for_year) is choose_period
    assert _route("month:3", SalaryStates.waiting_for_month) is choose_month
    assert _route(keyboards.DATE_TODAY, SalaryStates.waiting_for_advance_date) is choose_advance_date
    assert _route(keyboards.DATE_SKIP, SalaryStates.waiting_for_salary_date) is choose_salary_date
    assert _route(keyboards.CANCEL, SalaryStates.waiting_for_salary) is cancel_by_button


def test_routing_button_from_finished_input_is_stale():
    assert _route("period:2026:10") is stale_button
    assert _route("month:3", SalaryStates.waiting_for_advance) is stale_button
    assert _route(keyboards.DATE_TODAY, SalaryStates.waiting_for_salary) is stale_button


# --- Доступ ------------------------------------------------------------------------


def test_middleware_blocks_buttons_of_unknown_user(monkeypatch):
    answered = []

    async def fake_answer(self, text=None, **kwargs):
        answered.append(text)

    monkeypatch.setattr(CallbackQuery, "answer", fake_answer)
    callback = CallbackQuery(
        id="1", from_user=User(id=999, is_bot=False, first_name="x"), chat_instance="c", data="cancel"
    )
    called = []

    async def handler(_event, _data):
        called.append(True)

    asyncio.run(BotAccessMiddleware(frozenset({123}))(handler, callback, {}))

    assert called == []
    assert answered == ["Доступ к этому боту запрещён."]

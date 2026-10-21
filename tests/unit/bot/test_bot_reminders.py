import asyncio
from datetime import date

import pytest
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import SendMessage

from bot.handlers.salary import (
    SalaryStates,
    enter_by_reminder,
    keep_advance,
    keep_salary,
    snooze_reminder,
    stale_button,
)
from bot.keyboards import salary as keyboards
from bot.reminders import format_reminder, send_due_reminders
from bot_fakes import FakeCallback, FakeMessage, FakeState, buttons as _buttons, route_callback as _route


def _reminder(kind="advance", evening=1, year=2026, month=10):
    return {"kind": kind, "year": year, "month": month, "due_date": date(2026, 10, 28), "evening": evening}


class FakeBot:
    def __init__(self, fail_for=()):
        self.sent = []
        self._fail_for = set(fail_for)

    async def send_message(self, chat_id, text, **kwargs):
        if chat_id in self._fail_for:
            raise TelegramNetworkError(method=SendMessage(chat_id=chat_id, text=text), message="proxy down")
        self.sent.append((chat_id, text, kwargs.get("reply_markup")))


@pytest.fixture
def api(monkeypatch):
    calls = {"marked": 0, "reminders": []}
    monkeypatch.setattr(
        "bot.reminders.SalaryAPI.get_reminders_to_send",
        lambda: {"success": True, "data": calls["reminders"]},
    )

    def mark():
        calls["marked"] += 1
        return {"success": True}

    monkeypatch.setattr("bot.reminders.SalaryAPI.mark_reminders_sent", mark)
    return calls


# --- Текст и кнопки напоминания ------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "evening", "expected"),
    [
        ("advance", 1, "🔔 Сегодня обычно приходит аванс за октябрь 2026 (28-го). Пришёл? Внесите сумму."),
        ("advance", 3, "🔔 Напоминаю: аванс за октябрь 2026 ещё не внесён (обычно приходит 28-го)."),
        ("salary", 1, "🔔 Сегодня обычно приходит зарплата за октябрь 2026 (28-го). Пришла? Внесите сумму."),
        ("salary", 2, "🔔 Напоминаю: зарплата за октябрь 2026 ещё не внесена (обычно приходит 28-го)."),
    ],
)
def test_reminder_text(kind, evening, expected):
    assert format_reminder(_reminder(kind, evening)) == expected


def test_reminder_buttons():
    assert _buttons(keyboards.reminder_keyboard("salary", 2026, 9)) == [
        ("Внести зарплату за сентябрь", "remind:salary:2026:9"),
        ("Не напоминать об этой выплате", "snooze:salary:2026:9"),
    ]
    assert keyboards.parse_payment("snooze:salary:2026:9") == ("salary", 2026, 9)
    with pytest.raises(ValueError):
        keyboards.parse_payment("remind:bonus:2026:9")


# --- Отправка --------------------------------------------------------------------------


def test_reminders_are_sent_to_every_allowed_user(api):
    api["reminders"] = [_reminder()]
    bot = FakeBot()

    delivered = asyncio.run(send_due_reminders(bot, (1, 2)))

    assert delivered == 2
    assert [chat for chat, _, _ in bot.sent] == [1, 2]
    assert _buttons(bot.sent[0][2])[0] == ("Внести аванс за октябрь", "remind:advance:2026:10")
    assert api["marked"] == 1


def test_evening_is_closed_when_nothing_to_remind(api):
    asyncio.run(send_due_reminders(FakeBot(), (1,)))

    assert api["marked"] == 1


def test_undelivered_reminders_are_retried(api):
    # Нет сети — вечер не закрывается, бот повторит через несколько минут
    api["reminders"] = [_reminder()]

    delivered = asyncio.run(send_due_reminders(FakeBot(fail_for={1}), (1,)))

    assert delivered == 0
    assert api["marked"] == 0


def test_api_error_sends_nothing(monkeypatch):
    monkeypatch.setattr(
        "bot.reminders.SalaryAPI.get_reminders_to_send", lambda: {"success": False, "message": "db"}
    )
    bot = FakeBot()

    assert asyncio.run(send_due_reminders(bot, (1,))) == 0
    assert bot.sent == []


# --- Кнопки под напоминанием ----------------------------------------------------------


@pytest.fixture
def filled_september(monkeypatch):
    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.get_salary",
        lambda year, month: {"success": True, "data": {
            "year": year, "month_name": "Сентябрь", "advance": 14170.55, "salary": 0.0,
            "advance_date": "28.09.2026", "salary_date": "",
        }},
    )


def test_enter_by_reminder_opens_that_month_and_offers_saved_advance(filled_september):
    callback = FakeCallback("remind:salary:2026:9", FakeMessage("🔔 Напоминаю"))
    state = FakeState({"year": 2020, "month": 1}, SalaryStates.waiting_for_salary)  # начатый ввод сбрасывается

    asyncio.run(enter_by_reminder(callback, state))

    assert state.data["year"] == 2026 and state.data["month"] == 9
    assert state.current_state == SalaryStates.waiting_for_advance
    prompt, kwargs = callback.message.answers[-1]
    assert prompt == "Введите сумму аванса:"
    assert _buttons(kwargs["reply_markup"])[0] == ("Оставить 14 170,55", "keep:advance")
    assert callback.message.edited == ["🔔 Напоминаю\n➜ Вношу данные"]


def test_keep_advance_takes_saved_amount():
    callback = FakeCallback("keep:advance", FakeMessage("Введите сумму аванса:"))
    state = FakeState({"year": 2026, "month": 9, "existing_advance": 14170.55}, SalaryStates.waiting_for_advance)

    asyncio.run(keep_advance(callback, state))

    assert state.data["advance"] == 14170.55
    assert state.current_state == SalaryStates.waiting_for_advance_date


def test_salary_step_offers_keep_only_when_salary_saved(monkeypatch):
    from bot.handlers.salary import _accept_advance_date

    with_salary = FakeState({"existing_salary": 42183.19}, SalaryStates.waiting_for_advance_date)
    without = FakeState({"existing_salary": 0.0}, SalaryStates.waiting_for_advance_date)
    msg_with, msg_without = FakeMessage(), FakeMessage()

    asyncio.run(_accept_advance_date(msg_with, with_salary, None))
    asyncio.run(_accept_advance_date(msg_without, without, None))

    assert _buttons(msg_with.answers[-1][1]["reply_markup"])[0] == ("Оставить 42 183,19", "keep:salary")
    assert msg_without.answers[-1][1]["reply_markup"] is None


def test_keep_salary_takes_saved_amount():
    callback = FakeCallback("keep:salary", FakeMessage("Введите сумму зарплаты:"))
    state = FakeState({"existing_salary": 42183.19}, SalaryStates.waiting_for_salary)

    asyncio.run(keep_salary(callback, state))

    assert state.data["salary"] == 42183.19
    assert state.current_state == SalaryStates.waiting_for_salary_date


def test_snooze_button(monkeypatch):
    snoozed = []
    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.snooze_reminder",
        lambda kind, year, month: snoozed.append((kind, year, month)) or {"success": True},
    )
    callback = FakeCallback("snooze:advance:2026:10", FakeMessage("🔔 Сегодня"))

    asyncio.run(snooze_reminder(callback))

    assert snoozed == [("advance", 2026, 10)]
    assert callback.message.edited == ["🔔 Сегодня\n➜ Больше не напомню об этой выплате"]


def test_routing_reminder_buttons_work_in_any_state():
    assert _route("remind:advance:2026:10") is enter_by_reminder
    assert _route("remind:advance:2026:10", SalaryStates.waiting_for_salary) is enter_by_reminder
    assert _route("snooze:advance:2026:10") is snooze_reminder


def test_routing_keep_only_on_its_step():
    assert _route("keep:advance", SalaryStates.waiting_for_advance) is keep_advance
    assert _route("keep:salary", SalaryStates.waiting_for_salary) is keep_salary
    assert _route("keep:advance", SalaryStates.waiting_for_salary) is stale_button

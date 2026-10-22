import asyncio

import pytest

from bot.handlers.salary import _format_existing_month_warning, ask_note, cmd_cancel, process_note, process_non_text
from bot.presenters.year_report import format_year_details
from bot.states import NoteStates
from bot_fakes import SAMPLE_YEARS, FakeCallback, FakeMessage, FakeState, buttons, route_message


@pytest.fixture
def note_api(monkeypatch):
    calls = []

    def fake_set_note(year, month, note):
        calls.append((year, month, note))
        if note and len(note) > 200:
            return {"success": False, "message": "Заметка длиннее 200 символов (201)"}
        return {"success": True, "data": {"year": year, "month": month, "month_name": "Октябрь", "note": note}}

    monkeypatch.setattr("bot.handlers.salary.SalaryAPI.set_note", fake_set_note)
    return calls


def test_note_button_asks_for_text():
    callback = FakeCallback("note:2026:10", FakeMessage("✅ Запись успешно сохранена!"))
    state = FakeState()

    asyncio.run(ask_note(callback, state))

    assert state.current_state == NoteStates.waiting_for_text
    assert state.data == {"year": 2026, "month": 10}
    text, kwargs = callback.message.answers[-1]
    assert "к месяцу «Октябрь 2026»" in text
    assert buttons(kwargs["reply_markup"]) == [("Отмена", "cancel")]


def test_note_is_saved_and_menu_returns(note_api):
    msg = FakeMessage("отпуск 2 недели")
    state = FakeState({"year": 2026, "month": 10}, NoteStates.waiting_for_text)

    asyncio.run(process_note(msg, state))

    assert note_api == [(2026, 10, "отпуск 2 недели")]
    assert state.cleared is True
    text, kwargs = msg.answers[-1]
    assert text == "📝 Заметка к месяцу «Октябрь 2026»: отпуск 2 недели"
    assert kwargs["reply_markup"].keyboard[0][0].text == "➕ Внести"


def test_dash_deletes_note(note_api):
    msg = FakeMessage("-")

    asyncio.run(process_note(msg, FakeState({"year": 2026, "month": 10}, NoteStates.waiting_for_text)))

    assert note_api == [(2026, 10, "")]
    assert msg.answers[-1][0] == "Заметка к месяцу «Октябрь 2026» удалена."


def test_too_long_note_is_asked_again(note_api):
    msg = FakeMessage("я" * 201)
    state = FakeState({"year": 2026, "month": 10}, NoteStates.waiting_for_text)

    asyncio.run(process_note(msg, state))

    assert state.cleared is False
    assert "короче" in msg.answers[-1][0]


def test_note_shown_in_details_and_in_filled_month_warning():
    data = [dict(year) for year in SAMPLE_YEARS]
    data[0] = {**data[0], "months": [dict(m) for m in data[0]["months"]]}
    data[0]["months"][8]["note"] = "премия за квартал"

    assert "  📝 премия за квартал" in format_year_details(data, 2026)
    warning = _format_existing_month_warning({
        "year": 2026, "month_name": "Сентябрь", "advance": 1, "salary": 2, "note": "отпуск",
    })
    assert "  📝 отпуск\n" in warning


def test_routing_in_note_state():
    from bot.handlers.reports import cmd_current

    assert route_message("отпуск", NoteStates.waiting_for_text) is process_note
    assert route_message("отмена", NoteStates.waiting_for_text) is cmd_cancel
    assert route_message("📅 Этот год", NoteStates.waiting_for_text) is cmd_current
    assert route_message(None, NoteStates.waiting_for_text) is process_non_text

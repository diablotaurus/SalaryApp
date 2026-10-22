import asyncio

import pytest

from bot.handlers.extras import (
    choose_extra_date,
    choose_extra_kind,
    choose_extra_month,
    cmd_extra,
    parse_month_year,
    process_extra_amount,
    process_extra_date,
    process_extra_month,
)
from bot.handlers.reports import cmd_current
from bot.handlers.salary import cmd_add, cmd_cancel, process_non_text
from bot.keyboards import menu
from bot.presenters.year_report import format_annual_report, format_year_details, format_year_overview
from bot.states import ExtraStates
from bot_fakes import SAMPLE_YEARS, FakeCallback, FakeMessage, FakeState, buttons, route_callback, route_message


@pytest.fixture
def extras_api(monkeypatch):
    saved = []
    monkeypatch.setattr(
        "bot.handlers.extras.SalaryAPI.add_extra_payment",
        lambda *args: saved.append(args) or {"success": True, "data": {"id": 1}},
    )
    monkeypatch.setattr(
        "bot.handlers.extras.SalaryAPI.get_salary",
        lambda year, month: {"success": True, "data": {"total": 120000.0}},
    )
    return saved


def test_menu_button_starts_with_kinds():
    msg, state = FakeMessage(menu.MENU_EXTRA), FakeState({"year": 1999})

    asyncio.run(cmd_extra(msg, state))

    assert state.current_state == ExtraStates.waiting_for_kind
    assert state.cleared is True  # прежний ввод сброшен
    assert [text for text, _ in buttons(msg.answers[-1][1]["reply_markup"])] == [
        "Отпускные", "Премия", "Больничные", "Прочее", "Отмена",
    ]


def test_full_flow_by_buttons(extras_api, monkeypatch):
    monkeypatch.setattr("bot.handlers.extras.DateUtils.get_current_period", lambda: (2026, 10))
    monkeypatch.setattr("bot.handlers.common.moscow_today", lambda: __import__("datetime").date(2026, 10, 22))
    state = FakeState(current_state=ExtraStates.waiting_for_kind)

    kind = FakeCallback("extrakind:bonus", FakeMessage("Какая доп. выплата?"))
    asyncio.run(choose_extra_kind(kind, state))
    assert buttons(kind.message.answers[-1][1]["reply_markup"])[:2] == [
        ("Октябрь 2026", "extraperiod:2026:10"), ("Сентябрь 2026", "extraperiod:2026:9"),
    ]

    asyncio.run(choose_extra_month(FakeCallback("extraperiod:2026:10", FakeMessage("месяц")), state))
    amount = FakeMessage("20 000")
    asyncio.run(process_extra_amount(amount, state))
    assert state.current_state == ExtraStates.waiting_for_date

    done = FakeCallback("date:today", FakeMessage("Дата получения"))
    asyncio.run(choose_extra_date(done, state))

    assert extras_api == [(2026, 10, "bonus", 20000.0, "22.10.2026")]
    assert state.cleared is True
    text, kwargs = done.message.answers[-1]
    assert text == "✅ Премия: 20 000,00 руб. — октябрь 2026\nИтого за месяц: 120 000,00 руб."
    assert kwargs["reply_markup"].keyboard[0][0].text == menu.MENU_ADD


def test_typed_month_and_date(extras_api):
    state = FakeState({"kind": "vacation"}, ExtraStates.waiting_for_month)

    asyncio.run(process_extra_month(FakeMessage("08.2026"), state))
    assert state.data["year"] == 2026 and state.data["month"] == 8
    asyncio.run(process_extra_amount(FakeMessage("35000"), state))
    asyncio.run(process_extra_date(FakeMessage("-"), state))

    assert extras_api == [(2026, 8, "vacation", 35000.0, None)]


@pytest.mark.parametrize("text", ["13.2026", "август", "08.1999"])
def test_bad_month_is_asked_again(text):
    msg, state = FakeMessage(text), FakeState({"kind": "bonus"}, ExtraStates.waiting_for_month)

    asyncio.run(process_extra_month(msg, state))

    assert state.current_state == ExtraStates.waiting_for_month
    assert "например 08.2026" in msg.answers[-1][0]


def test_zero_amount_is_asked_again():
    msg, state = FakeMessage("0"), FakeState({"kind": "bonus"}, ExtraStates.waiting_for_amount)

    asyncio.run(process_extra_amount(msg, state))

    assert state.current_state == ExtraStates.waiting_for_amount
    assert "больше нуля" in msg.answers[-1][0]


def test_parse_month_year():
    assert parse_month_year("8/2026") == (2026, 8)
    assert parse_month_year(" 12.2025 ") == (2025, 12)
    assert parse_month_year("2026.08") is None


def test_routing_menu_and_cancel_pass_through_extras_steps():
    # Шаги доп. выплаты не перехватывают команды, кнопки меню и «отмену»
    assert route_message("20000", ExtraStates.waiting_for_amount) is process_extra_amount
    assert route_message("отмена", ExtraStates.waiting_for_amount) is cmd_cancel
    assert route_message("/cancel", ExtraStates.waiting_for_date) is cmd_cancel
    assert route_message(menu.MENU_ADD, ExtraStates.waiting_for_amount) is cmd_add
    assert route_message(menu.MENU_YEAR, ExtraStates.waiting_for_month) is cmd_current
    assert route_message(menu.MENU_EXTRA, ExtraStates.waiting_for_amount) is cmd_extra
    assert route_message(None, ExtraStates.waiting_for_amount) is process_non_text
    assert route_message("/extra") is cmd_extra


def test_routing_extra_buttons():
    assert route_callback("extrakind:sick", ExtraStates.waiting_for_kind) is choose_extra_kind
    assert route_callback("extraperiod:2026:10", ExtraStates.waiting_for_month) is choose_extra_month
    assert route_callback("date:skip", ExtraStates.waiting_for_date) is choose_extra_date


def test_reports_show_extras():
    data = [dict(item) for item in SAMPLE_YEARS]
    data[0] = {**data[0], "summary": {**data[0]["summary"], "total_extras": 55000.0, "regular_average_monthly": 100000.0},
               "months": [dict(m) for m in data[0]["months"]]}
    data[0]["months"][8]["extras"] = [
        {"kind_name": "Отпускные", "amount": 35000.0}, {"kind_name": "Премия", "amount": 20000.0},
    ]

    overview = format_year_overview(data, 2026)
    assert "в т.ч. доп. выплаты: 55 000,00" in overview
    assert "Регулярный доход: 100 000,00 в месяц" in overview
    assert "  Доп.: Отпускные 35 000,00, Премия 20 000,00" in format_year_details(data, 2026)
    assert "в т.ч. доп. выплаты: 55 000,00" in format_annual_report(data, 2026)
    assert "доп. выплаты" not in format_year_overview(SAMPLE_YEARS, 2026)

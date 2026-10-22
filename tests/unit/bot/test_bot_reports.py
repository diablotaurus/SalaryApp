import asyncio
import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText

from bot.handlers.reports import cmd_current, cmd_year_stats, cmd_years, show_year, show_year_details
from bot.handlers.salary import SalaryStates, cmd_add, cmd_start, process_advance
from bot.keyboards import menu
from bot.presenters.year_report import (
    format_month_comparison,
    format_year_details,
    format_year_overview,
    format_years_summary,
)
from bot_fakes import SAMPLE_YEARS as DATA, FakeCallback, FakeMessage, buttons, route_message as _route_message


@pytest.fixture
def years_api(monkeypatch):
    monkeypatch.setattr(
        "bot.handlers.reports.SalaryAPI.get_all_grouped_by_year", lambda: {"success": True, "data": DATA}
    )


# --- Тексты -------------------------------------------------------------------------


def test_year_overview_is_compact_and_compares_average():
    text = format_year_overview(DATA, 2026)

    assert text.splitlines()[:5] == [
        "📅 2026 год",
        "",
        "Итого: 345 000,00",
        "Среднемесячно: 110 000,00 (+10,0 % к 2025)",
        "Месяцев с данными: 4",
    ]
    assert text.endswith("Последние месяцы:\n• М10 — 15 000,00\n• М9 — 120 000,00\n• М2 — 110 000,00")


def test_year_overview_without_previous_year_has_no_comparison():
    assert "к 2022" not in format_year_overview(DATA, 2023)
    assert format_year_overview(DATA, 2027) == "📅 2027 год\n\nДанных пока нет."


def test_year_details_lists_filled_months_in_order():
    text = format_year_details(DATA, 2026)

    assert text.startswith("Статистика за 2026 год\n\nМ1\n  Аванс: 33 333,33  •  28.01.2026")
    assert text.endswith("Итого за год: 345 000,00")
    assert format_year_details(DATA, 2024) == "Нет данных за 2024 год."


def test_years_summary():
    text = format_years_summary(DATA)

    assert "2026 — 345 000,00 (4 мес.)\n   в среднем 110 000,00 в месяц, +10,0 % к 2025" in text
    assert "2025 — 1 200 000,00 (12 мес.)\n   в среднем 100 000,00 в месяц\n" in text  # 2024 нет
    assert text.endswith("Всего за 3 года: 1 595 000,00")
    assert "Внесите первый месяц" in format_years_summary([])


@pytest.mark.parametrize(
    ("percent", "expected"),
    [
        (7.4, "📈 На 7 % выше среднего за последние 12 месяцев (100 000,00)."),
        (-12.6, "📉 На 13 % ниже среднего за последние 12 месяцев (100 000,00)."),
        (0.4, "📊 На уровне среднего за последние 12 месяцев (100 000,00)."),
    ],
)
def test_month_comparison_line(percent, expected):
    assert format_month_comparison({"percent": percent, "average": 100000.0}) == expected


def test_month_comparison_absent_without_data():
    assert format_month_comparison(None) is None
    assert format_month_comparison({"percent": None, "average": 0}) is None


# --- Клавиатуры -----------------------------------------------------------------------


def test_main_menu_buttons():
    markup = menu.main_menu()

    assert [[b.text for b in row] for row in markup.keyboard] == [
        ["➕ Внести", "📅 Этот год"], ["📆 По годам", "📊 Отчёты"], ["💰 Доп. выплата", "❓ Помощь"],
    ]
    assert markup.is_persistent and markup.resize_keyboard


def test_year_navigation_skips_years_without_data():
    assert buttons(menu.year_overview_keyboard(2025, [2023, 2025, 2026])) == [
        ("◀ 2023", "year:2023"), ("Подробно", "yeardet:2025"), ("2026 ▶", "year:2026"),
        ("📈 График", "chartyear:2025"),
    ]
    # Текущий год ещё без данных: назад — к последнему году с данными
    assert buttons(menu.year_overview_keyboard(2027, [2025, 2026])) == [
        ("◀ 2026", "year:2026"), ("Подробно", "yeardet:2027"), ("📈 График", "chartyear:2027"),
    ]


# --- Обработчики ----------------------------------------------------------------------


def test_this_year_button_shows_current_moscow_year(years_api, monkeypatch):
    monkeypatch.setattr("bot.handlers.reports.DateUtils.get_current_period", lambda: (2026, 10))
    msg = FakeMessage(menu.MENU_YEAR)

    asyncio.run(cmd_current(msg))

    text, kwargs = msg.answers[-1]
    assert text.startswith("📅 2026 год")
    assert buttons(kwargs["reply_markup"])[0] == ("◀ 2025", "year:2025")


def test_year_command(years_api):
    msg = FakeMessage("/2025")

    asyncio.run(cmd_year_stats(msg))

    assert msg.answers[-1][0].startswith("📅 2025 год")


def test_years_button_offers_year_buttons(years_api):
    msg = FakeMessage(menu.MENU_YEARS)

    asyncio.run(cmd_years(msg))

    text, kwargs = msg.answers[-1]
    assert text.startswith("📆 Итоги по годам")
    assert [data for _, data in buttons(kwargs["reply_markup"])] == ["year:2026", "year:2025", "year:2023"]


def test_api_error_is_reported(monkeypatch):
    monkeypatch.setattr("bot.handlers.reports.SalaryAPI.get_all_grouped_by_year", lambda: {"success": False})
    msg = FakeMessage("/years")

    asyncio.run(cmd_years(msg))

    assert msg.answers == [("Ошибка при получении данных.", {})]


def test_year_buttons_edit_the_same_message(years_api):
    callback = FakeCallback("yeardet:2026", FakeMessage("📅 2026 год"))

    asyncio.run(show_year_details(callback))
    asyncio.run(show_year(FakeCallback("year:2025", callback.message)))

    assert callback.message.edited[0].startswith("Статистика за 2026 год")
    assert callback.message.edited[1].startswith("📅 2025 год")
    assert callback.message.answers == []  # листание не плодит сообщения


def test_old_message_gets_report_as_new_message(years_api):
    error = TelegramBadRequest(method=EditMessageText(text="x"), message="message can't be edited")
    callback = FakeCallback("year:2025", FakeMessage("старое", edit_error=error))

    asyncio.run(show_year(callback))

    assert callback.message.answers[-1][0].startswith("📅 2025 год")


def test_same_year_pressed_again_is_quiet(years_api):
    error = TelegramBadRequest(method=EditMessageText(text="x"), message="message is not modified")
    callback = FakeCallback("year:2025", FakeMessage("📅 2025 год", edit_error=error))

    asyncio.run(show_year(callback))

    assert callback.message.answers == []


def test_help_shows_menu():
    msg = FakeMessage("/start")

    asyncio.run(cmd_start(msg))

    text, kwargs = msg.answers[-1]
    assert "📅 Этот год — сводка" in text
    assert kwargs["reply_markup"].keyboard[0][0].text == menu.MENU_ADD


# --- Маршрутизация (настоящие фильтры aiogram, порядок роутеров как в bot/main.py) ---------


def test_menu_buttons_work_in_the_middle_of_input():
    # Раньше ввода: «Этот год» не принимается шагом как сумма
    assert _route_message(menu.MENU_YEAR, SalaryStates.waiting_for_advance) is cmd_current
    assert _route_message(menu.MENU_YEARS, SalaryStates.waiting_for_salary) is cmd_years
    assert _route_message(menu.MENU_ADD, SalaryStates.waiting_for_salary_date) is cmd_add
    assert _route_message(menu.MENU_HELP, SalaryStates.waiting_for_month) is cmd_start
    assert _route_message("1000", SalaryStates.waiting_for_advance) is process_advance


def test_year_commands_routing():
    assert _route_message("/current") is cmd_current
    assert _route_message("/years") is cmd_years
    assert _route_message("/2024") is cmd_year_stats


def test_saved_month_shows_comparison_and_note_button(monkeypatch):
    from bot.handlers.salary import process_salary_date
    from bot_fakes import FakeState

    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.add_salary",
        lambda *args: {"success": True, "data": {
            "year": 2026, "month_name": "Октябрь", "advance": 15000.0, "salary": 100000.0,
        }},
    )
    monkeypatch.setattr(
        "bot.handlers.salary.SalaryAPI.compare_with_recent_average",
        lambda year, month: {"success": True, "data": {"percent": 4.6, "average": 110000.0}},
    )
    msg = FakeMessage("-")
    state = FakeState({"year": 2026, "month": 10, "advance": 15000.0, "salary": 100000.0, "advance_date": None})

    asyncio.run(process_salary_date(msg, state))

    text, kwargs = msg.answers[-1]
    assert text.endswith("📈 На 5 % выше среднего за последние 12 месяцев (110 000,00).")
    assert buttons(kwargs["reply_markup"]) == [("📝 Заметка к месяцу", "note:2026:10")]

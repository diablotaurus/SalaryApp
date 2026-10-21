import asyncio

import pytest

from bot.handlers.reports import cmd_records, cmd_reports, send_excel, send_year_chart, send_years_chart, show_records
from bot.keyboards import menu
from bot.presenters import charts
from bot.presenters.year_report import format_annual_report, format_records, format_year_overview
from bot.reminders import send_annual_report
from bot_fakes import SAMPLE_YEARS as DATA, FakeCallback, FakeMessage, buttons, route_message as _route_message

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def years_api(monkeypatch):
    monkeypatch.setattr(
        "bot.handlers.reports.SalaryAPI.get_all_grouped_by_year", lambda: {"success": True, "data": DATA}
    )


# --- Тексты ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("last_month", "line"),
    [
        (9, "Январь–сентябрь: +3,9 % к тому же периоду 2025"),
        (1, "Январь: +3,9 % к тому же периоду 2025"),
    ],
)
def test_overview_shows_year_to_date_for_unfinished_year(last_month, line):
    ytd = {"year": 2026, "last_month": last_month, "percent": 3.94}

    assert line in format_year_overview(DATA, 2026, ytd)


def test_overview_skips_year_to_date_for_full_year():
    ytd = {"year": 2025, "last_month": 12, "percent": 9.2}

    assert "периоду" not in format_year_overview(DATA, 2025, ytd)


def test_records_text():
    records = {
        "top_months": [
            {"year": 2026, "month": 8, "month_name": "Август", "total": 158785.3},
            {"year": 2025, "month": 3, "month_name": "Март", "total": 140000.0},
        ],
        "best_year": {"year": 2025, "total": 1233751.04},
        "best_average_year": {"year": 2026, "average": 107798.43},
    }

    assert format_records(records) == (
        "🏆 Рекорды\n\nЛучшие месяцы:\n1. Август 2026 — 158 785,30\n2. Март 2025 — 140 000,00\n\n"
        "Лучший год: 2025 — 1 233 751,04\nСамое высокое среднемесячное: 2026 — 107 798,43"
    )
    assert "пока нет" in format_records({"top_months": []})


def test_annual_report_text():
    text = format_annual_report(DATA, 2026)

    assert text.startswith("🎉 Итоги 2026 года\n\nЗаработано: 345 000,00\nСреднемесячно: 110 000,00 (+10,0 % к 2025)")
    assert text.endswith("Лучший месяц года: М9 — 120 000,00")
    assert len(text) <= 1024  # подпись к фото в Telegram


# --- Графики (настоящий matplotlib) -----------------------------------------------------------


def test_year_chart_is_png_with_and_without_previous_year():
    assert charts.year_chart(DATA, 2026).startswith(PNG_SIGNATURE)
    assert charts.year_chart(DATA, 2023).startswith(PNG_SIGNATURE)  # 2022 нет — одна серия


def test_years_chart_is_png():
    assert charts.years_chart(DATA).startswith(PNG_SIGNATURE)


def test_axis_labels_in_thousands():
    assert charts._thousands(158785.3) == "159 тыс."
    assert charts._thousands(1200000) == "1 200 тыс."
    assert charts._thousands(0) == "0"


# --- Обработчики ------------------------------------------------------------------------------


def test_reports_menu(monkeypatch):
    monkeypatch.setattr("bot.handlers.reports.DateUtils.get_current_period", lambda: (2026, 10))
    msg = FakeMessage(menu.MENU_REPORTS)

    asyncio.run(cmd_reports(msg))

    assert [data for _, data in buttons(msg.answers[-1][1]["reply_markup"])] == [
        "chartyear:2026", "chartyears", "records", "export:excel",
    ]


def test_year_chart_is_sent_as_photo(years_api):
    callback = FakeCallback("chartyear:2026")

    asyncio.run(send_year_chart(callback))

    kind, payload = callback.message.answers[-1]
    assert kind == "photo"
    assert payload["file"].data.startswith(PNG_SIGNATURE)
    assert payload["caption"] == "📈 2026 по месяцам"


def test_years_chart_is_sent_as_photo(years_api):
    callback = FakeCallback("chartyears")

    asyncio.run(send_years_chart(callback))

    assert callback.message.answers[-1][0] == "photo"


def test_records_by_button_and_command(monkeypatch):
    monkeypatch.setattr(
        "bot.handlers.reports.SalaryAPI.get_records",
        lambda: {"success": True, "data": {"top_months": [
            {"year": 2026, "month": 8, "month_name": "Август", "total": 1.0},
        ]}},
    )
    callback, msg = FakeCallback("records"), FakeMessage("/records")

    asyncio.run(show_records(callback))
    asyncio.run(cmd_records(msg))

    assert callback.message.answers[-1][0].startswith("🏆 Рекорды")
    assert msg.answers[-1][0].startswith("🏆 Рекорды")


def test_excel_is_sent_and_removed_from_disk(monkeypatch, tmp_path):
    export = tmp_path / "salary_export_20261022_120000.xlsx"
    export.write_bytes(b"PK\x03\x04excel")
    monkeypatch.setattr(
        "bot.handlers.reports.SalaryAPI.export_data",
        lambda fmt: {"success": True, "data": {"filepath": str(export), "format": fmt}},
    )
    callback = FakeCallback("export:excel")

    asyncio.run(send_excel(callback))

    kind, payload = callback.message.answers[-1]
    assert kind == "document"
    assert payload["file"].data == b"PK\x03\x04excel"
    assert payload["file"].filename == export.name
    assert not export.exists()  # копия данных не остаётся в exports/


def test_routing_reports_button_mid_input():
    from bot.handlers.salary import SalaryStates

    assert _route_message(menu.MENU_REPORTS, SalaryStates.waiting_for_advance) is cmd_reports
    assert _route_message("/records") is cmd_records


# --- Годовой итог -------------------------------------------------------------------------------


class FakeBot:
    def __init__(self):
        self.photos = []

    async def send_photo(self, chat_id, photo, **kwargs):
        self.photos.append((chat_id, photo, kwargs))


@pytest.fixture
def annual_api(monkeypatch):
    state = {"year": 2026, "marked": []}
    monkeypatch.setattr(
        "bot.reminders.SalaryAPI.get_annual_report_year", lambda: {"success": True, "data": state["year"]}
    )
    monkeypatch.setattr(
        "bot.reminders.SalaryAPI.get_all_grouped_by_year", lambda: {"success": True, "data": DATA}
    )
    monkeypatch.setattr(
        "bot.reminders.SalaryAPI.mark_annual_report_sent",
        lambda year: state["marked"].append(year) or {"success": True},
    )
    return state


def test_annual_report_is_sent_once_with_chart(annual_api):
    bot = FakeBot()

    delivered = asyncio.run(send_annual_report(bot, (1, 2)))

    assert delivered == 2
    chat_id, photo, kwargs = bot.photos[0]
    assert photo.data.startswith(PNG_SIGNATURE)
    assert kwargs["caption"].startswith("🎉 Итоги 2026 года")
    assert annual_api["marked"] == [2026]


def test_annual_report_waits_until_due(annual_api):
    annual_api["year"] = None
    bot = FakeBot()

    assert asyncio.run(send_annual_report(bot, (1,))) == 0
    assert bot.photos == [] and annual_api["marked"] == []

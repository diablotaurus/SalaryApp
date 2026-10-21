"""
Отчёты бота: сводка года (листается по годам), подробно по месяцам, итоги
по годам, графики картинкой, рекорды и выгрузка в Excel.

Роутер подключается раньше роутера ввода: кнопки меню «Этот год»,
«По годам» и «Отчёты» работают и посреди ввода, не сбрасывая его.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from api.salary_api import SalaryAPI
from bot.keyboards import menu
from bot.presenters import charts
from bot.presenters.year_report import (
    format_records,
    format_year_details,
    format_year_overview,
    format_years_summary,
)
from core.utils.dates import DateUtils

router = Router()

DATA_ERROR = "Ошибка при получении данных."


def _years_data() -> Optional[list[dict]]:
    """Все годы со сводками и месяцами; None — ошибка получения данных."""
    response = SalaryAPI.get_all_grouped_by_year()
    if not response.get("success"):
        return None
    return response.get("data") or []


def _years(data: list[dict]) -> list[int]:
    return [int(item["year"]) for item in data]


def _year_to_date(year: int) -> Optional[dict]:
    """Год к году за тот же период (необязательная строка сводки)."""
    response = SalaryAPI.compare_year_to_date(year)
    return response.get("data") if response.get("success") else None


async def _send_year(message: types.Message, year: int) -> None:
    data = _years_data()
    if data is None:
        await message.answer(DATA_ERROR)
        return
    await message.answer(
        format_year_overview(data, year, _year_to_date(year)),
        reply_markup=menu.year_overview_keyboard(year, _years(data)),
    )


@router.message(Command("current"))
@router.message(F.text == menu.MENU_YEAR)
async def cmd_current(message: types.Message):
    year, _ = DateUtils.get_current_period()
    await _send_year(message, year)


@router.message(F.text.regexp(r"^/\d{4}$"))
async def cmd_year_stats(message: types.Message):
    await _send_year(message, int(message.text[1:]))


@router.message(Command("years"))
@router.message(F.text == menu.MENU_YEARS)
async def cmd_years(message: types.Message):
    data = _years_data()
    if data is None:
        await message.answer(DATA_ERROR)
        return
    markup = menu.years_keyboard(_years(data)) if data else None
    await message.answer(format_years_summary(data), reply_markup=markup)


async def _show(callback: types.CallbackQuery, text: str, markup: types.InlineKeyboardMarkup) -> None:
    """Показать отчёт в том же сообщении (листание без новых сообщений в чате)."""
    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "not modified" in str(exc):
            return  # нажали на тот же год — показывать нечего
        # Старое сообщение изменить нельзя — отправить отчёт новым
        await callback.message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith(menu.YEAR_PREFIX))
async def show_year(callback: types.CallbackQuery):
    year = menu.parse_year(callback.data)
    data = _years_data()
    if data is None:
        await callback.answer(DATA_ERROR)
        return
    await _show(
        callback,
        format_year_overview(data, year, _year_to_date(year)),
        menu.year_overview_keyboard(year, _years(data)),
    )


@router.callback_query(F.data.startswith(menu.YEAR_DETAILS_PREFIX))
async def show_year_details(callback: types.CallbackQuery):
    year = menu.parse_year(callback.data)
    data = _years_data()
    if data is None:
        await callback.answer(DATA_ERROR)
        return
    await _show(callback, format_year_details(data, year), menu.year_details_keyboard(year))


# --- Меню отчётов: графики, рекорды, Excel ----------------------------------------------


@router.message(Command("reports"))
@router.message(F.text == menu.MENU_REPORTS)
async def cmd_reports(message: types.Message):
    year, _ = DateUtils.get_current_period()
    await message.answer("📊 Отчёты — выберите:", reply_markup=menu.reports_keyboard(year))


@router.callback_query(F.data.startswith(menu.CHART_YEAR_PREFIX))
async def send_year_chart(callback: types.CallbackQuery):
    year = int(callback.data[len(menu.CHART_YEAR_PREFIX):])
    data = _years_data()
    await callback.answer()
    if data is None:
        await callback.message.answer(DATA_ERROR)
        return
    # Рисование занимает доли секунды — в отдельном потоке, чтобы бот не замирал
    png = await asyncio.to_thread(charts.year_chart, data, year)
    await callback.message.answer_photo(
        BufferedInputFile(png, filename=f"salary_{year}.png"), caption=f"📈 {year} по месяцам"
    )


@router.callback_query(F.data == menu.CHART_YEARS)
async def send_years_chart(callback: types.CallbackQuery):
    data = _years_data()
    await callback.answer()
    if not data:
        await callback.message.answer(DATA_ERROR if data is None else "Данных пока нет.")
        return
    png = await asyncio.to_thread(charts.years_chart, data)
    await callback.message.answer_photo(
        BufferedInputFile(png, filename="salary_years.png"), caption="📊 Среднемесячный доход по годам"
    )


def _records_text() -> str:
    response = SalaryAPI.get_records()
    return format_records(response["data"]) if response.get("success") else DATA_ERROR


@router.message(Command("records"))
async def cmd_records(message: types.Message):
    await message.answer(_records_text())


@router.callback_query(F.data == menu.RECORDS)
async def show_records(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(_records_text())


@router.callback_query(F.data == menu.EXPORT_EXCEL)
async def send_excel(callback: types.CallbackQuery):
    """Все данные файлом Excel; копия на диске сразу удаляется (как в web-экспорте)."""
    await callback.answer("Готовлю файл…")
    response = await asyncio.to_thread(SalaryAPI.export_data, "excel")
    if not response.get("success"):
        await callback.message.answer(response.get("message") or "Не удалось сформировать файл")
        return
    path = Path(response["data"]["filepath"])
    try:
        content = path.read_bytes()
    finally:
        path.unlink(missing_ok=True)
    await callback.message.answer_document(
        BufferedInputFile(content, filename=path.name), caption="📄 Все данные в Excel"
    )

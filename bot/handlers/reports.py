"""
Отчёты бота: сводка года (листается по годам), подробно по месяцам, итоги по годам.

Роутер подключается раньше роутера ввода: кнопки меню «Этот год» и
«По годам» работают и посреди ввода, не сбрасывая его.
"""
from __future__ import annotations

from typing import Optional

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command

from api.salary_api import SalaryAPI
from bot.keyboards import menu
from bot.presenters.year_report import format_year_details, format_year_overview, format_years_summary
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


async def _send_year(message: types.Message, year: int) -> None:
    data = _years_data()
    if data is None:
        await message.answer(DATA_ERROR)
        return
    await message.answer(
        format_year_overview(data, year),
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
    await _show(callback, format_year_overview(data, year), menu.year_overview_keyboard(year, _years(data)))


@router.callback_query(F.data.startswith(menu.YEAR_DETAILS_PREFIX))
async def show_year_details(callback: types.CallbackQuery):
    year = menu.parse_year(callback.data)
    data = _years_data()
    if data is None:
        await callback.answer(DATA_ERROR)
        return
    await _show(callback, format_year_details(data, year), menu.year_details_keyboard(year))

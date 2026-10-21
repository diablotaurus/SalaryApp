"""
Постоянное меню бота (кнопки под полем ввода) и навигация по отчётам.

Кнопки меню отправляют обычный текст, поэтому их обработчики регистрируются
раньше шагов ввода и работают в любом состоянии.
"""
from __future__ import annotations

from typing import Iterable

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

MENU_ADD = "➕ Внести"
MENU_YEAR = "📅 Этот год"
MENU_YEARS = "📆 По годам"
MENU_HELP = "❓ Помощь"

YEAR_PREFIX = "year:"            # year:2026 — сводка года
YEAR_DETAILS_PREFIX = "yeardet:"  # yeardet:2026 — подробно по месяцам


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_ADD), KeyboardButton(text=MENU_YEAR)],
            [KeyboardButton(text=MENU_YEARS), KeyboardButton(text=MENU_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите действие или введите команду",
    )


def _neighbours(year: int, years: Iterable[int]) -> tuple[int | None, int | None]:
    """Ближайшие годы с данными до и после выбранного."""
    years = sorted(set(years))
    previous = max((y for y in years if y < year), default=None)
    following = min((y for y in years if y > year), default=None)
    return previous, following


def year_overview_keyboard(year: int, years: Iterable[int]) -> InlineKeyboardMarkup:
    """Под сводкой года: листать годы и открыть подробно по месяцам."""
    previous, following = _neighbours(year, years)
    row = []
    if previous is not None:
        row.append(InlineKeyboardButton(text=f"◀ {previous}", callback_data=f"{YEAR_PREFIX}{previous}"))
    row.append(InlineKeyboardButton(text="Подробно", callback_data=f"{YEAR_DETAILS_PREFIX}{year}"))
    if following is not None:
        row.append(InlineKeyboardButton(text=f"{following} ▶", callback_data=f"{YEAR_PREFIX}{following}"))
    return InlineKeyboardMarkup(inline_keyboard=[row])


def year_details_keyboard(year: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ К сводке", callback_data=f"{YEAR_PREFIX}{year}")],
    ])


def years_keyboard(years: Iterable[int]) -> InlineKeyboardMarkup:
    """Под итогами по годам: открыть сводку любого года."""
    buttons = [
        InlineKeyboardButton(text=str(year), callback_data=f"{YEAR_PREFIX}{year}")
        for year in sorted(set(years), reverse=True)
    ]
    rows = [buttons[i:i + 4] for i in range(0, len(buttons), 4)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def parse_year(data: str) -> int:
    """«year:2026» / «yeardet:2026» -> 2026."""
    return int(data.split(":", 1)[1])

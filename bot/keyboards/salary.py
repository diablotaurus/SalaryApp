"""
Inline-кнопки диалога ввода зарплаты.

Кнопки дополняют ввод текстом, а не заменяют его: год, номер месяца
и дату по-прежнему можно напечатать.
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from core.utils.dates import DateUtils

CANCEL = "cancel"
PERIOD_PREFIX = "period:"
MONTH_PREFIX = "month:"
DATE_TODAY = "date:today"
DATE_SKIP = "date:skip"

MONTHS_PER_ROW = 4


def _cancel_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="Отмена", callback_data=CANCEL)]


def period_label(year: int, month: int) -> str:
    """«Октябрь 2026» — подпись кнопки и подтверждение выбора."""
    return f"{DateUtils.get_month_name(month)} {year}"


def period_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    """Текущий и прошлый месяц одной кнопкой (зарплату за прошлый часто вносят в следующем)."""
    previous = DateUtils.get_previous_month(year, month)
    buttons = [
        InlineKeyboardButton(text=period_label(y, m), callback_data=f"{PERIOD_PREFIX}{y}:{m}")
        for y, m in ((year, month), previous)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons, _cancel_row()])


def months_keyboard() -> InlineKeyboardMarkup:
    """12 месяцев сеткой 3×4 — после того как год введён текстом."""
    buttons = [
        InlineKeyboardButton(text=DateUtils.get_month_name(month, short=True), callback_data=f"{MONTH_PREFIX}{month}")
        for month in range(1, 13)
    ]
    rows = [buttons[i:i + MONTHS_PER_ROW] for i in range(0, len(buttons), MONTHS_PER_ROW)]
    return InlineKeyboardMarkup(inline_keyboard=[*rows, _cancel_row()])


def date_keyboard(today_text: str) -> InlineKeyboardMarkup:
    """Дата выплаты: «Сегодня» (по МСК) или «Пропустить»."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"Сегодня, {today_text}", callback_data=DATE_TODAY),
            InlineKeyboardButton(text="Пропустить", callback_data=DATE_SKIP),
        ],
        _cancel_row(),
    ])


def parse_period(data: str) -> tuple[int, int]:
    """«period:2026:10» -> (2026, 10)."""
    year, month = data[len(PERIOD_PREFIX):].split(":")
    return int(year), int(month)


def parse_month(data: str) -> int:
    """«month:10» -> 10."""
    return int(data[len(MONTH_PREFIX):])

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
KEEP_PREFIX = "keep:"      # keep:advance — оставить сохранённую сумму
REMIND_PREFIX = "remind:"  # remind:salary:2026:9 — открыть ввод по напоминанию
SNOOZE_PREFIX = "snooze:"  # snooze:salary:2026:9 — больше не напоминать

# Винительный падеж для кнопки «Внести …»
PAYMENT_ACCUSATIVE = {"advance": "аванс", "salary": "зарплату"}

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


def keep_amount_keyboard(kind: str, amount_text: str) -> InlineKeyboardMarkup:
    """Месяц уже заполнен: оставить сохранённую сумму одной кнопкой."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Оставить {amount_text}", callback_data=f"{KEEP_PREFIX}{kind}")],
        _cancel_row(),
    ])


def reminder_keyboard(kind: str, year: int, month: int) -> InlineKeyboardMarkup:
    """Кнопки под напоминанием: внести выплату или больше о ней не напоминать."""
    suffix = f"{kind}:{year}:{month}"
    month_name = DateUtils.get_month_name(month).lower()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Внести {PAYMENT_ACCUSATIVE[kind]} за {month_name}",
            callback_data=f"{REMIND_PREFIX}{suffix}",
        )],
        [InlineKeyboardButton(text="Не напоминать об этой выплате", callback_data=f"{SNOOZE_PREFIX}{suffix}")],
    ])


def parse_payment(data: str) -> tuple[str, int, int]:
    """«remind:salary:2026:9» / «snooze:…» -> ("salary", 2026, 9)."""
    _, kind, year, month = data.split(":")
    if kind not in PAYMENT_ACCUSATIVE:
        raise ValueError(f"Неизвестный вид выплаты: {kind}")
    return kind, int(year), int(month)


def parse_period(data: str) -> tuple[int, int]:
    """«period:2026:10» -> (2026, 10)."""
    year, month = data[len(PERIOD_PREFIX):].split(":")
    return int(year), int(month)


def parse_month(data: str) -> int:
    """«month:10» -> 10."""
    return int(data[len(MONTH_PREFIX):])

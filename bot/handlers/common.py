"""
Общее для диалогов ввода бота: разбор ответов (суммы, даты), кнопки дат,
подтверждение выбора кнопкой. Используется вводом месяца и доп. выплат.
"""
from __future__ import annotations

from typing import Optional

from aiogram import types
from aiogram.exceptions import TelegramBadRequest

from api.salary_api import SalaryAPI
from bot.keyboards import menu
from bot.keyboards import salary as keyboards
from core.utils.clock import moscow_today
from core.utils.money import MoneyUtils

CANCEL_WORDS = {"отмена", "отменить"}
ASK_DATE_AGAIN = "Введите дату (ДД.ММ.ГГГГ) или '-' чтобы пропустить:"
DATE_FORMAT = "%d.%m.%Y"
DATE_BUTTONS = {keyboards.DATE_TODAY, keyboards.DATE_SKIP}


def parse_optional_date(text: str) -> Optional[str]:
    value = text.strip()
    return None if value in ("-", "нет", "skip", "пропустить") else value


def is_cancel_text(message: types.Message) -> bool:
    return bool(message.text) and message.text.strip().lower() in CANCEL_WORDS


def is_step_answer(message: types.Message) -> bool:
    """
    Ответ на шаг ввода, а не команда, кнопка меню или «отмена».

    Нужен роутерам, подключённым раньше роутера ввода месяца: так команды,
    меню и отмена проходят дальше к своим обработчикам в любом состоянии.
    """
    text = (message.text or "").strip()
    return bool(text) and not text.startswith("/") and text not in menu.MENU_TEXTS and text.lower() not in CANCEL_WORDS


async def read_date(message: types.Message, field_label: str) -> tuple[bool, Optional[str]]:
    """
    Прочитать дату выплаты из ответа: (ок, дата ДД.ММ.ГГГГ или None при пропуске).

    Дата проверяется сразу на своём шаге: раньше ошибка обнаруживалась
    только при сохранении, и весь введённый месяц приходилось вводить заново.
    """
    value = parse_optional_date(message.text)
    if value is None:
        return True, None
    check = SalaryAPI.validate_payment_date(value, field_label)
    if check.get("success"):
        return True, check.get("data")
    await message.answer(f"❌ {check.get('message')}\n{ASK_DATE_AGAIN}")
    return False, None


async def read_amount(message: types.Message, field_label: str, ask_again: str) -> Optional[float]:
    """
    Прочитать сумму из ответа по тем же правилам, что в desktop (MoneyUtils.parse_amount).

    Понимает пробелы (в т.ч. неразрывные из банковских приложений) и запятую:
    «87 432,71». Раньше бот принимал только float(): сумма с пробелами
    отклонялась, а «nan» или «1e5» проходили шаг и падали лишь при сохранении,
    и весь введённый месяц терялся.
    """
    try:
        amount = MoneyUtils.parse_amount(message.text, field_label)
    except ValueError as exc:
        error = str(exc)
        await message.answer(f"❌ {error[:1].upper()}{error[1:]}\n{ask_again}")
        return None
    if amount < 0:
        await message.answer(f"Сумма не может быть отрицательной. {ask_again}")
        return None
    return amount


def date_keyboard():
    """Кнопки «Сегодня» (по МСК) и «Пропустить» под вопросом о дате выплаты."""
    return keyboards.date_keyboard(moscow_today().strftime(DATE_FORMAT))


async def confirm_choice(callback: types.CallbackQuery, choice: str) -> None:
    """Убрать нажатую кнопку и дописать выбор в то же сообщение."""
    await callback.answer()
    message = callback.message
    try:
        await message.edit_text(f"{message.text}\n➜ {choice}")
    except TelegramBadRequest:
        # Сообщение слишком старое или уже изменено — выбор всё равно принят
        pass


async def chosen_date(callback: types.CallbackQuery) -> Optional[str]:
    """Дата по кнопке: сегодня по МСК или None («Пропустить»)."""
    value = moscow_today().strftime(DATE_FORMAT) if callback.data == keyboards.DATE_TODAY else None
    await confirm_choice(callback, value or "без даты")
    return value

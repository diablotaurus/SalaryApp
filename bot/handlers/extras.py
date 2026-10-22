"""
Ввод доп. выплаты в боте: «💰 Доп. выплата» → вид → месяц → сумма → дата.

Выплата относится к месяцу получения. Роутер подключается раньше роутера
ввода месяца: кнопка меню работает в любом состоянии, а шаги этого ввода
пропускают дальше команды, кнопки меню и «отмену» (is_step_answer).
"""
from __future__ import annotations

import re
from typing import Optional

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from api.salary_api import SalaryAPI
from bot.handlers.common import (
    DATE_BUTTONS,
    chosen_date,
    confirm_choice,
    date_keyboard,
    is_step_answer,
    read_amount,
    read_date,
)
from bot.keyboards import menu
from bot.keyboards import salary as keyboards
from bot.states import ExtraStates
from core.models.extra_payment import EXTRA_KINDS
from core.utils.dates import DateUtils
from core.utils.money import MoneyUtils

router = Router()

MONTH_YEAR = re.compile(r"^(\d{1,2})[./](\d{4})$")


def _period(year: int, month: int) -> str:
    return f"{DateUtils.get_month_name(month).lower()} {year}"


@router.message(Command("extra"))
@router.message(F.text == menu.MENU_EXTRA)
async def cmd_extra(message: types.Message, state: FSMContext):
    await state.clear()  # новый ввод начинается с чистого листа
    await state.set_state(ExtraStates.waiting_for_kind)
    await message.answer("Какая доп. выплата?", reply_markup=keyboards.extra_kind_keyboard())


@router.callback_query(ExtraStates.waiting_for_kind, F.data.startswith(keyboards.EXTRA_KIND_PREFIX))
async def choose_extra_kind(callback: types.CallbackQuery, state: FSMContext):
    kind = keyboards.parse_extra_kind(callback.data)
    await confirm_choice(callback, EXTRA_KINDS[kind])
    await state.update_data(kind=kind)
    await state.set_state(ExtraStates.waiting_for_month)
    year, month = DateUtils.get_current_period()
    await callback.message.answer(
        "К какому месяцу отнести? Обычно — к месяцу, когда деньги пришли.\n"
        "Выберите кнопкой или введите месяц и год, например 08.2026:",
        reply_markup=keyboards.extra_period_keyboard(year, month),
    )


async def _ask_amount(message: types.Message, state: FSMContext, year: int, month: int) -> None:
    await state.update_data(year=year, month=month)
    await state.set_state(ExtraStates.waiting_for_amount)
    kind = (await state.get_data())["kind"]
    await message.answer(f"Сумма ({EXTRA_KINDS[kind].lower()}, {_period(year, month)}):")


@router.callback_query(ExtraStates.waiting_for_month, F.data.startswith(keyboards.EXTRA_PERIOD_PREFIX))
async def choose_extra_month(callback: types.CallbackQuery, state: FSMContext):
    year, month = keyboards.parse_extra_period(callback.data)
    await confirm_choice(callback, keyboards.period_label(year, month))
    await _ask_amount(callback.message, state, year, month)


def parse_month_year(text: str) -> Optional[tuple[int, int]]:
    """«08.2026» / «8/2026» -> (2026, 8); None — не похоже на месяц."""
    match = MONTH_YEAR.match(text.strip())
    if not match:
        return None
    month, year = int(match.group(1)), int(match.group(2))
    if 1 <= month <= 12 and 2000 <= year <= 2100:
        return year, month
    return None


@router.message(ExtraStates.waiting_for_month, is_step_answer)
async def process_extra_month(message: types.Message, state: FSMContext):
    period = parse_month_year(message.text)
    if period is None:
        await message.answer("Введите месяц и год, например 08.2026, или выберите кнопкой.")
        return
    await _ask_amount(message, state, *period)


@router.message(ExtraStates.waiting_for_amount, is_step_answer)
async def process_extra_amount(message: types.Message, state: FSMContext):
    amount = await read_amount(message, "сумма", "Введите сумму:")
    if amount is None:
        return
    if amount <= 0:
        await message.answer("Сумма доп. выплаты должна быть больше нуля. Введите сумму:")
        return
    await state.update_data(amount=amount)
    await state.set_state(ExtraStates.waiting_for_date)
    await message.answer(
        "Дата получения (ДД.ММ.ГГГГ) или '-' чтобы пропустить:", reply_markup=date_keyboard()
    )


async def _save_extra(message: types.Message, state: FSMContext, paid_date: Optional[str]) -> None:
    data = await state.get_data()
    response = SalaryAPI.add_extra_payment(data["year"], data["month"], data["kind"], data["amount"], paid_date)
    await state.clear()
    if not response.get("success"):
        await message.answer(f"❌ Ошибка: {response.get('message')}", reply_markup=menu.main_menu())
        return
    month = SalaryAPI.get_salary(data["year"], data["month"])
    total = month["data"]["total"] if month.get("success") else None
    text = (
        f"✅ {EXTRA_KINDS[data['kind']]}: {MoneyUtils.format_amount(data['amount'])} "
        f"— {_period(data['year'], data['month'])}"
    )
    if total is not None:
        text += f"\nИтого за месяц: {MoneyUtils.format_amount(total)}"
    await message.answer(text, reply_markup=menu.main_menu())


@router.message(ExtraStates.waiting_for_date, is_step_answer)
async def process_extra_date(message: types.Message, state: FSMContext):
    ok, paid_date = await read_date(message, "даты выплаты")
    if not ok:
        return
    await _save_extra(message, state, paid_date)


@router.callback_query(ExtraStates.waiting_for_date, F.data.in_(DATE_BUTTONS))
async def choose_extra_date(callback: types.CallbackQuery, state: FSMContext):
    await _save_extra(callback.message, state, await chosen_date(callback))

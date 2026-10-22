"""FSM states for adding a salary record through Telegram."""

from aiogram.fsm.state import State, StatesGroup


class SalaryStates(StatesGroup):
    """States used by the salary input dialog."""

    waiting_for_year = State()
    waiting_for_month = State()
    waiting_for_advance = State()
    waiting_for_advance_date = State()
    waiting_for_salary = State()
    waiting_for_salary_date = State()


class ExtraStates(StatesGroup):
    """Доп. выплата: вид → месяц получения → сумма → дата."""

    waiting_for_kind = State()
    waiting_for_month = State()
    waiting_for_amount = State()
    waiting_for_date = State()


class NoteStates(StatesGroup):
    """Заметка к уже внесённому месяцу (кнопка после сохранения)."""

    waiting_for_text = State()

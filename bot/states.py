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

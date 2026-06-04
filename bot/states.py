"""
Состояния для FSM (Finite State Machine)
"""
from aiogram.dispatcher.filters.state import State, StatesGroup


class SalaryStates(StatesGroup):
    """Состояния для добавления зарплаты"""
    waiting_for_year = State()
    waiting_for_month = State()
    waiting_for_advance = State()
    waiting_for_salary = State()
"""Telegram command and FSM handlers for salary operations."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext

from api.salary_api import SalaryAPI
from bot.states import SalaryStates
from core.utils.money import MoneyUtils


router = Router()

CANCEL_WORDS = {"отмена", "отменить"}
ASK_DATE_AGAIN = "Введите дату (ДД.ММ.ГГГГ) или '-' чтобы пропустить:"


def _parse_optional_date(text: str) -> Optional[str]:
    value = text.strip()
    return None if value in ("-", "нет", "skip", "пропустить") else value


def _is_cancel_text(message: types.Message) -> bool:
    return bool(message.text) and message.text.strip().lower() in CANCEL_WORDS


async def _read_date(message: types.Message, field_label: str) -> tuple[bool, Optional[str]]:
    """
    Прочитать дату выплаты из ответа: (ок, дата ДД.ММ.ГГГГ или None при пропуске).

    Дата проверяется сразу на своём шаге: раньше ошибка обнаруживалась
    только при сохранении, и весь введённый месяц приходилось вводить заново.
    """
    value = _parse_optional_date(message.text)
    if value is None:
        return True, None
    check = SalaryAPI.validate_payment_date(value, field_label)
    if check.get("success"):
        return True, check.get("data")
    await message.answer(f"❌ {check.get('message')}\n{ASK_DATE_AGAIN}")
    return False, None


def _format_existing_month_warning(data: dict) -> str:
    """Предупреждение, что у месяца уже есть данные и новые значения их заменят."""
    advance = MoneyUtils.format_amount_plain(float(data.get("advance", 0) or 0))
    salary = MoneyUtils.format_amount_plain(float(data.get("salary", 0) or 0))
    return (
        f"⚠️ За {data.get('month_name', '')} {data.get('year', '')} уже есть данные:\n"
        f"  Аванс: {advance}  •  {data.get('advance_date') or '-'}\n"
        f"  Зарплата: {salary}  •  {data.get('salary_date') or '-'}\n"
        "Новые значения заменят их, пропуск даты («-») оставит прежнюю.\n"
        "Отмена — /cancel"
    )


def _format_year_table(year: int) -> str:
    response = SalaryAPI.get_salaries_by_year(year)
    if not response.get("success"):
        return "Ошибка при получении данных."

    rows = response.get("data", [])
    if not rows:
        return f"Нет данных за {year} год."

    month_blocks = [f"Статистика за {year} год"]
    total_year = 0.0
    for row in sorted(rows, key=lambda item: item["month"]):
        advance = float(row.get("advance", 0) or 0)
        salary = float(row.get("salary", 0) or 0)
        total = float(row.get("total", 0) or (advance + salary))
        total_year += total
        month_blocks.append(
            "\n".join(
                [
                    str(row.get("month_name", "")),
                    f"  Аванс: {MoneyUtils.format_amount_plain(advance)}  •  {row.get('advance_date') or '-'}",
                    f"  Зарплата: {MoneyUtils.format_amount_plain(salary)}  •  {row.get('salary_date') or '-'}",
                    f"  Итого: {MoneyUtils.format_amount_plain(total)}",
                ]
            )
        )

    month_blocks.append(f"Итого за год: {MoneyUtils.format_amount_plain(total_year)}")
    return "\n\n".join(month_blocks)


def _format_current_year_table() -> str:
    return _format_year_table(datetime.now().year)


@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в бот учета зарплаты!\n\n"
        "Доступные команды:\n"
        "/add - Добавить запись о зарплате\n"
        "/current - Показать статистику за текущий год\n"
        "/2025 - Показать статистику за 2025 год\n"
        "/cancel - Отменить начатый ввод\n"
        "/help - Показать эту справку\n\n"
        "Формат даты: ДД.ММ.ГГГГ (можно пропустить, введя '-')"
    )


# Отмена регистрируется раньше обработчиков шагов ввода:
# иначе «/cancel» был бы принят шагом как ответ (например, как сумма).
@router.message(Command("cancel"))
@router.message(StateFilter(SalaryStates), _is_cancel_text)
async def cmd_cancel(message: types.Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Сейчас нечего отменять.")
        return
    await state.clear()
    await message.answer("Ввод отменён, данные не сохранены.")


@router.message(Command("current"))
async def cmd_current(message: types.Message):
    await message.answer(_format_current_year_table())


@router.message(F.text.regexp(r"^/\d{4}$"))
async def cmd_year_stats(message: types.Message):
    await message.answer(_format_year_table(int(message.text[1:])))


@router.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    await state.set_state(SalaryStates.waiting_for_year)
    await message.answer("Введите год (например, 2024):")


@router.message(SalaryStates.waiting_for_year, F.text)
async def process_year(message: types.Message, state: FSMContext):
    try:
        year = int(message.text)
        if not 2000 <= year <= 2100:
            await message.answer("Введите корректный год (2000-2100):")
            return
        await state.update_data(year=year)
        await state.set_state(SalaryStates.waiting_for_month)
        await message.answer("Введите номер месяца (1-12):")
    except ValueError:
        await message.answer("Введите число (год):")


@router.message(SalaryStates.waiting_for_month, F.text)
async def process_month(message: types.Message, state: FSMContext):
    try:
        month = int(message.text)
        if not 1 <= month <= 12:
            await message.answer("Введите корректный месяц (1-12):")
            return
        await state.update_data(month=month)
        await state.set_state(SalaryStates.waiting_for_advance)

        # Месяц уже заполнен — показать, что будет заменено (раньше перезапись была молчаливой)
        data = await state.get_data()
        existing = SalaryAPI.get_salary(data["year"], month)
        if existing.get("success"):
            await message.answer(_format_existing_month_warning(existing["data"]))

        await message.answer("Введите сумму аванса:")
    except ValueError:
        await message.answer("Введите число (месяц):")


@router.message(SalaryStates.waiting_for_advance, F.text)
async def process_advance(message: types.Message, state: FSMContext):
    try:
        advance = float(message.text.replace(",", "."))
        if advance < 0:
            await message.answer("Сумма не может быть отрицательной. Введите аванс:")
            return
        await state.update_data(advance=advance)
        await state.set_state(SalaryStates.waiting_for_advance_date)
        await message.answer("Введите дату аванса (ДД.ММ.ГГГГ) или '-' чтобы пропустить:")
    except ValueError:
        await message.answer("Введите число (сумма аванса):")


@router.message(SalaryStates.waiting_for_advance_date, F.text)
async def process_advance_date(message: types.Message, state: FSMContext):
    ok, advance_date = await _read_date(message, "даты аванса")
    if not ok:
        return
    await state.update_data(advance_date=advance_date)
    await state.set_state(SalaryStates.waiting_for_salary)
    await message.answer("Введите сумму зарплаты:")


@router.message(SalaryStates.waiting_for_salary, F.text)
async def process_salary(message: types.Message, state: FSMContext):
    try:
        salary = float(message.text.replace(",", "."))
        if salary < 0:
            await message.answer("Сумма не может быть отрицательной. Введите зарплату:")
            return
        await state.update_data(salary=salary)
        await state.set_state(SalaryStates.waiting_for_salary_date)
        await message.answer("Введите дату зарплаты (ДД.ММ.ГГГГ) или '-' чтобы пропустить:")
    except ValueError:
        await message.answer("Введите число (сумма зарплаты):")


@router.message(SalaryStates.waiting_for_salary_date, F.text)
async def process_salary_date(message: types.Message, state: FSMContext):
    ok, salary_date = await _read_date(message, "даты зарплаты")
    if not ok:
        return
    data = await state.get_data()
    response = SalaryAPI.add_salary(
        data["year"],
        data["month"],
        data["advance"],
        data["salary"],
        data.get("advance_date"),
        salary_date,
    )

    if response.get("success"):
        salary_data = response["data"]
        total = salary_data["advance"] + salary_data["salary"]
        await message.answer(
            "✅ Запись успешно сохранена!\n\n"
            f"📅 {salary_data['month_name']} {salary_data['year']} г.\n"
            f"💵 Аванс: {salary_data['advance']:,.2f} руб.\n"
            f"💰 Зарплата: {salary_data['salary']:,.2f} руб.\n"
            f"📊 Итого: {total:,.2f} руб."
        )
    else:
        await message.answer(f"❌ Ошибка: {response.get('message')}")

    await state.clear()


# Регистрируется последним: стикер, фото или голосовое на любом шаге ввода
# раньше приводили к ошибке в обработчике (у таких сообщений нет текста).
@router.message(StateFilter(SalaryStates))
async def process_non_text(message: types.Message):
    await message.answer("Пришлите ответ текстом или /cancel для отмены.")

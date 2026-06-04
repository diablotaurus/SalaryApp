"""
Telegram-бот для учета зарплаты на основе aiogram v3.

Бот предоставляет интерфейс для добавления записей о зарплатах
и просмотра данных через Telegram. Поддерживает диалоговый режим
с использованием FSM (Finite State Machine) для пошагового ввода данных.
"""

import asyncio
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from api.salary_api import SalaryAPI
from core.config.settings import config
from core.database.migrations import apply_all_migrations
from core.utils.money import MoneyUtils


# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
# Используется ротируемое логирование для предотвращения переполнения диска
handler = RotatingFileHandler(
    filename=str(config.logging.bot_log_file),  # Путь к лог-файлу из конфигурации
    maxBytes=5 * 1024 * 1024,  # 5 MiB - максимальный размер файла до ротации
    backupCount=3,  # Количество backup файлов
    encoding="utf-8",  # Кодировка UTF-8 для поддержки кириллицы
)
handler.setFormatter(logging.Formatter(str(config.logging.format)))  # Формат логов из конфигурации

root = logging.getLogger()
root.setLevel(getattr(logging, str(config.logging.level).upper(), logging.INFO))
root.handlers.clear()
root.addHandler(handler)
logger = logging.getLogger(__name__)


# ==================== ЗАГРУЗКА ТОКЕНА БОТА ====================
def _load_bot_token() -> str:
    """
    Загрузить токен бота из переменных окружения или файла.
    
    Порядок поиска токена:
    1. Переменная окружения SALARYAPP_BOT_TOKEN
    2. Переменная окружения BOT_TOKEN
    3. Файл bot/.env
    
    Returns:
        str: Токен бота
        
    Raises:
        RuntimeError: Если токен не найден ни в одном источнике
    """
    # Поиск токена в переменных окружения
    env_token = os.getenv("SALARYAPP_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    if env_token:
        return env_token.strip()

    # Поиск токена в файле .env в директории бота
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() in ("BOT_TOKEN", "SALARYAPP_BOT_TOKEN", "API_TOKEN"):
                token = value.strip().strip('"').strip("'")
                if token:
                    return token

    raise RuntimeError("BOT_TOKEN не найден. Укажите в bot/.env или переменной окружения.")


# ==================== FSM СОСТОЯНИЯ ДЛЯ ДИАЛОГА ====================
class SalaryStates(StatesGroup):
    """
    Класс состояний FSM (Finite State Machine) для диалога добавления зарплаты.
    
    Каждое состояние соответствует шагу ввода данных:
    - waiting_for_year: Ожидание ввода года
    - waiting_for_month: Ожидание ввода месяца
    - waiting_for_advance: Ожидание ввода суммы аванса
    - waiting_for_advance_date: Ожидание ввода даты аванса (можно пропустить)
    - waiting_for_salary: Ожидание ввода суммы зарплаты
    - waiting_for_salary_date: Ожидание ввода даты зарплаты (можно пропустить)
    """
    waiting_for_year = State()
    waiting_for_month = State()
    waiting_for_advance = State()
    waiting_for_advance_date = State()
    waiting_for_salary = State()
    waiting_for_salary_date = State()


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def _parse_optional_date(text: str) -> Optional[str]:
    """
    Разобрать опциональную дату из текста.
    
    Args:
        text: Текст с датой или специальным значением
        
    Returns:
        Optional[str]: Дата или None если указано специальное значение
        
    Специальные значения (пропуск даты):
        - "-", "нет", "skip", "пропустить"
    """
    value = text.strip()
    if value in ("-", "нет", "skip", "пропустить"):
        return None
    return value


def _format_year_table(year: int) -> str:
    """
    Сформировать компактный список с данными за выбранный год.

    Returns:
        str: Отформатированный текст для удобного чтения в Telegram
    """
    response = SalaryAPI.get_salaries_by_year(year)
    if not response.get("success"):
        return "Ошибка при получении данных."

    rows = response.get("data", [])
    if not rows:
        return f"Нет данных за {year} год."

    month_blocks = [f"Статистика за {year} год"]
    total_year = 0.0
    for row in sorted(rows, key=lambda x: x["month"]):
        month = row.get("month_name", "")
        advance = float(row.get("advance", 0) or 0)
        salary = float(row.get("salary", 0) or 0)
        total = float(row.get("total", 0) or (advance + salary))
        total_year += total
        advance_date = row.get("advance_date") or "-"
        salary_date = row.get("salary_date") or "-"

        month_blocks.append(
            "\n".join(
                [
                    str(month),
                    f"  Аванс: {MoneyUtils.format_amount_plain(advance)}  •  {advance_date}",
                    f"  Зарплата: {MoneyUtils.format_amount_plain(salary)}  •  {salary_date}",
                    f"  Итого: {MoneyUtils.format_amount_plain(total)}",
                ]
            )
        )

    month_blocks.append(f"Итого за год: {MoneyUtils.format_amount_plain(total_year)}")
    return "\n\n".join(month_blocks)


def _format_current_year_table() -> str:
    """
    Сформировать компактный список с данными за текущий год.

    Returns:
        str: Отформатированный текст для удобного чтения в Telegram
    """
    return _format_year_table(datetime.now().year)


# ==================== СОЗДАНИЕ И НАСТРОЙКА ROUTER ====================
router = Router()


# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_start(message: types.Message):
    """
    Обработчик команд /start и /help.
    
    Отправляет приветственное сообщение со списком доступных команд.
    """
    welcome_text = (
        "👋 Добро пожаловать в бот учета зарплаты!\n\n"
        "Доступные команды:\n"
        "/add - Добавить запись о зарплате\n"
        "/current - Показать статистику за текущий год\n"
        "/2025 - Показать статистику за 2025 год\n"
        "/help - Показать эту справку\n\n"
        "Формат даты: ДД.ММ.ГГГГ (можно пропустить, введя '-')"
    )
    await message.answer(welcome_text)


@router.message(Command("current"))
async def cmd_current(message: types.Message):
    """
    Обработчик команды /current.

    Отправляет компактный список с данными за текущий год.
    """
    table = _format_current_year_table()
    await message.answer(table)


@router.message(F.text.regexp(r"^/\d{4}$"))
async def cmd_year_stats(message: types.Message):
    """
    Обработчик команды вида /2025.

    Отправляет компактный список с данными за указанный год.
    """
    year = int(message.text[1:])
    table = _format_year_table(year)
    await message.answer(table)


@router.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    """
    Обработчик команды /add.
    
    Начинает диалог добавления записи о зарплате.
    Устанавливает первое состояние FSM.
    """
    await state.set_state(SalaryStates.waiting_for_year)
    await message.answer("Введите год (например, 2024):")


# ==================== ОБРАБОТЧИКИ СОСТОЯНИЙ FSM ====================
@router.message(SalaryStates.waiting_for_year)
async def process_year(message: types.Message, state: FSMContext):
    """
    Обработчик ввода года.
    
    Валидация:
        - Проверка что введено число
        - Проверка диапазона года (2000-2100)
    """
    try:
        year = int(message.text)
        if year < 2000 or year > 2100:
            await message.answer("Введите корректный год (2000-2100):")
            return
        await state.update_data(year=year)
        await state.set_state(SalaryStates.waiting_for_month)
        await message.answer("Введите номер месяца (1-12):")
    except ValueError:
        await message.answer("Введите число (год):")


@router.message(SalaryStates.waiting_for_month)
async def process_month(message: types.Message, state: FSMContext):
    """
    Обработчик ввода месяца.
    
    Валидация:
        - Проверка что введено число
        - Проверка диапазона месяца (1-12)
    """
    try:
        month = int(message.text)
        if month < 1 or month > 12:
            await message.answer("Введите корректный месяц (1-12):")
            return
        await state.update_data(month=month)
        await state.set_state(SalaryStates.waiting_for_advance)
        await message.answer("Введите сумму аванса:")
    except ValueError:
        await message.answer("Введите число (месяц):")


@router.message(SalaryStates.waiting_for_advance)
async def process_advance(message: types.Message, state: FSMContext):
    """
    Обработчик ввода суммы аванса.
    
    Валидация:
        - Проверка что введено число (поддерживает запятую как разделитель)
        - Проверка что сумма не отрицательная
    """
    try:
        advance = float(message.text.replace(",", "."))  # Поддержка запятой как разделителя
        if advance < 0:
            await message.answer("Сумма не может быть отрицательной. Введите аванс:")
            return
        await state.update_data(advance=advance)
        await state.set_state(SalaryStates.waiting_for_advance_date)
        await message.answer("Введите дату аванса (ДД.ММ.ГГГГ) или '-' чтобы пропустить:")
    except ValueError:
        await message.answer("Введите число (сумма аванса):")


@router.message(SalaryStates.waiting_for_advance_date)
async def process_advance_date(message: types.Message, state: FSMContext):
    """
    Обработчик ввода даты аванса.
    
    Поддерживает пропуск ввода специальными значениями.
    """
    advance_date = _parse_optional_date(message.text)
    await state.update_data(advance_date=advance_date)
    await state.set_state(SalaryStates.waiting_for_salary)
    await message.answer("Введите сумму зарплаты:")


@router.message(SalaryStates.waiting_for_salary)
async def process_salary(message: types.Message, state: FSMContext):
    """
    Обработчик ввода суммы зарплаты.
    
    Валидация:
        - Проверка что введено число
        - Проверка что сумма не отрицательная
    """
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


@router.message(SalaryStates.waiting_for_salary_date)
async def process_salary_date(message: types.Message, state: FSMContext):
    """
    Обработчик ввода даты зарплаты и финализации диалога.
    
    Выполняет:
        - Парсинг опциональной даты
        - Получение всех данных из FSM
        - Вызов API для сохранения записи
        - Отправка результата пользователю
        - Очистка состояния FSM
    """
    salary_date = _parse_optional_date(message.text)
    data = await state.get_data()

    # Вызов API для сохранения данных
    response = SalaryAPI.add_salary(
        data["year"],
        data["month"],
        data["advance"],
        data["salary"],
        data.get("advance_date"),
        salary_date,
    )

    # Формирование ответа пользователю
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

    # Очистка состояния FSM
    await state.clear()


# ==================== ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА ====================
async def main():
    """
    Основная асинхронная функция запуска бота.
    
    Выполняет:
        1. Применение миграций базы данных
        2. Создание экземпляра бота с загруженным токеном
        3. Настройку диспетчера с MemoryStorage
        4. Запуск long-polling
    """
    # Применение миграций БД при запуске
    apply_all_migrations()

    # Создание экземпляра бота
    bot = Bot(token=_load_bot_token())
    
    # Настройка хранилища состояний (в памяти)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    # Запуск бота
    logger.info("Бот запущен...")
    await dp.start_polling(bot)


# Точка входа для запуска бота
if __name__ == "__main__":
    asyncio.run(main())

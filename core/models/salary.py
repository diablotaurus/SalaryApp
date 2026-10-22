"""
Модели данных для работы с зарплатами.

Содержит Data-классы для представления сущностей системы.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.utils.clock import utc_now
from core.utils.dates import DateUtils


@dataclass
class Salary:
    """Модель записи о зарплате за конкретный месяц"""
    id: Optional[int] = None  # Идентификатор записи (автоинкремент в БД)
    year: int = 0  # Год
    month: int = 0  # Месяц (1-12)
    advance: float = 0.0  # Сумма аванса
    salary: float = 0.0  # Сумма зарплаты
    advance_date: Optional[datetime] = None  # Дата получения аванса (календарная дата)
    salary_date: Optional[datetime] = None  # Дата получения зарплаты (календарная дата)
    created_at: datetime = None  # Момент создания записи, timezone-aware UTC
    note: Optional[str] = None  # Заметка к месяцу («отпуск», «повышение»)

    def __post_init__(self):
        """Инициализация после создания экземпляра"""
        if self.created_at is None:
            self.created_at = utc_now()  # Текущий момент по умолчанию

    @property
    def total(self) -> float:
        """Общая сумма (аванс + зарплата)"""
        return self.advance + self.salary

    @property
    def month_name(self) -> str:
        """Название месяца на русском языке"""
        return DateUtils.get_month_name(self.month)

    def to_dict(self) -> dict:
        """Преобразование объекта Salary в словарь для API/UI"""
        return {
            "id": self.id,
            "year": self.year,
            "month": self.month,
            "advance": self.advance,
            "salary": self.salary,
            "total": self.total,
            "month_name": self.month_name,
            "advance_date": self._format_date(self.advance_date),
            "salary_date": self._format_date(self.salary_date),
            "note": self.note or "",
        }

    @staticmethod
    def _format_date(value: Optional[datetime]) -> str:
        """Форматирование даты в строку для отображения"""
        if not value:
            return ""
        return DateUtils.format_date(value)
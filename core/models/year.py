from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, List

from core.utils.clock import moscow_now
from .salary import Salary


def is_payment_complete(record: Any, now: datetime) -> bool:
    """
    Выплачена ли зарплата за месяц записи (единое правило для всех средних).

    Месяц учитывается, только если salary > 0 и:
      - salary_date задана и уже наступила, либо
      - salary_date не задана (старые данные), но месяц раньше текущего.

    salary_date — календарная дата, поэтому сравнивается с календарной датой
    now (её передают по МСК, см. core.utils.clock.moscow_now).
    """
    advance = float(getattr(record, "advance", 0) or 0)
    salary = float(getattr(record, "salary", 0) or 0)
    if salary <= 0 or advance + salary <= 0:
        return False

    salary_date = getattr(record, "salary_date", None)
    if salary_date is not None:
        payment_day = salary_date.date() if isinstance(salary_date, datetime) else salary_date
        return payment_day <= now.date()

    year = int(getattr(record, "year", 0) or 0)
    month = int(getattr(record, "month", 0) or 0)
    return (year, month) < (now.year, now.month)


def calculate_average_monthly(
    records: Iterable[Any], now: datetime | None = None, include_extras: bool = True
) -> float:
    """
    Среднее по месяцам с выплаченной зарплатой (is_payment_complete).

    include_extras=False — «регулярный доход»: только аванс и зарплата,
    без доп. выплат (отпускные, премии), чтобы они не искажали динамику.
    """
    current = now or moscow_now()
    totals = [
        float(getattr(record, "advance", 0) or 0)
        + float(getattr(record, "salary", 0) or 0)
        + (float(getattr(record, "extras_total", 0) or 0) if include_extras else 0.0)
        for record in records or []
        if is_payment_complete(record, current)
    ]
    return sum(totals) / len(totals) if totals else 0.0


@dataclass
class YearSummary:
    """Сводка по году"""
    year: int
    total_advance: float = 0.0
    total_salary: float = 0.0
    records: List[Salary] = None
    total_extras: float = 0.0
    month_details: dict = None
    
    def __post_init__(self):
        if self.records is None:
            self.records = []
        if self.month_details is None:
            self.month_details = {}
    
    @property
    def total(self) -> float:
        """Общая сумма за год, включая доп. выплаты"""
        return self.total_advance + self.total_salary + self.total_extras

    @property
    def average_monthly(self) -> float:
        """Среднемесячно всего (с доп. выплатами)"""
        return calculate_average_monthly(self.records)

    @property
    def regular_average_monthly(self) -> float:
        """Среднемесячный регулярный доход (аванс + зарплата)"""
        return calculate_average_monthly(self.records, include_extras=False)
    
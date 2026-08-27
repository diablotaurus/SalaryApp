from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, List
from .salary import Salary


def calculate_average_monthly(
    records: Iterable[Any], now: datetime | None = None
) -> float:
    """Calculate the average for months whose salary payment is complete."""
    current = now or datetime.now()
    totals: list[float] = []

    for record in records or []:
        advance = float(getattr(record, "advance", 0) or 0)
        salary = float(getattr(record, "salary", 0) or 0)
        if salary <= 0 or advance + salary <= 0:
            continue

        year = int(getattr(record, "year", 0) or 0)
        month = int(getattr(record, "month", 0) or 0)
        salary_date = getattr(record, "salary_date", None)
        if salary_date is not None:
            if salary_date > current:
                continue
        elif (year, month) >= (current.year, current.month):
            continue

        totals.append(advance + salary)

    return sum(totals) / len(totals) if totals else 0.0


@dataclass
class YearSummary:
    """Сводка по году"""
    year: int
    total_advance: float = 0.0
    total_salary: float = 0.0
    records: List[Salary] = None
    month_details: dict = None
    
    def __post_init__(self):
        if self.records is None:
            self.records = []
        if self.month_details is None:
            self.month_details = {}
    
    @property
    def total(self) -> float:
        """Общая сумма за год"""
        return self.total_advance + self.total_salary
    
    @property
    def average_monthly(self) -> float:
        """Среднемесячная зарплата"""
        return calculate_average_monthly(self.records)
    
    def add_record(self, salary: Salary):
        """Добавить запись о зарплате"""
        self.records.append(salary)
        self.total_advance += salary.advance
        self.total_salary += salary.salary
        self.month_details[salary.month] = salary.to_dict()

from dataclasses import dataclass
from typing import List
from .salary import Salary


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
        from core.services.statistics_service import StatisticsService

        return StatisticsService.calculate_average_monthly_from_records(self.records)
    
    def add_record(self, salary: Salary):
        """Добавить запись о зарплате"""
        self.records.append(salary)
        self.total_advance += salary.advance
        self.total_salary += salary.salary
        self.month_details[salary.month] = salary.to_dict()

from typing import List, Dict, Any
from core.models.year import YearSummary
from .analytics_repository import AnalyticsRepository
from .salary_repository import SalaryRepository


class YearRepository:
    """Репозиторий для работы с годовыми данными"""
    
    @staticmethod
    def get_all_years_summary() -> List[YearSummary]:
        """Получить сводку по всем годам"""
        years = SalaryRepository.get_years()
        return [SalaryRepository.get_year_summary(year) for year in years]
    
    @staticmethod
    def get_years_with_data() -> List[int]:
        """Получить список лет, по которым есть данные"""
        return SalaryRepository.get_years()
    
    @staticmethod
    def get_yearly_totals() -> List[Dict[str, Any]]:
        """Получить итоговые суммы по годам"""
        return AnalyticsRepository.get_yearly_totals()
    
    @staticmethod
    def get_monthly_averages(year: int = None) -> Dict[str, Any]:
        """Получить среднемесячные значения"""
        return AnalyticsRepository.get_monthly_averages(year)

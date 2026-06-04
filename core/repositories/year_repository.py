from typing import List, Dict, Any
from core.database.connection import DatabaseConnection
from core.models.year import YearSummary
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
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute("""
            SELECT 
                year,
                SUM(advance) as total_advance,
                SUM(salary) as total_salary,
                SUM(advance + salary) as total,
                COUNT(*) as months_count
            FROM salaries
            GROUP BY year
            ORDER BY year DESC
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_monthly_averages(year: int = None) -> Dict[str, Any]:
        """Получить среднемесячные значения"""
        conn = DatabaseConnection.get_connection()
        
        if year:
            cursor = conn.execute("""
                SELECT 
                    AVG(advance) as avg_advance,
                    AVG(salary) as avg_salary,
                    AVG(advance + salary) as avg_total
                FROM salaries
                WHERE year = ?
            """, (year,))
            result = dict(cursor.fetchone())
            result['year'] = year
        else:
            cursor = conn.execute("""
                SELECT 
                    AVG(advance) as avg_advance,
                    AVG(salary) as avg_salary,
                    AVG(advance + salary) as avg_total
                FROM salaries
            """)
            result = dict(cursor.fetchone())
            result['year'] = 'all'
        
        return result
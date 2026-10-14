"""
Сервис для работы с зарплатами.

Содержит бизнес-логику приложения по управлению записями о зарплатах.
Работает с репозиторием для доступа к данным и предоставляет методы для UI слоя.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from core.models.salary import Salary
from core.models.year import YearSummary
from core.repositories.salary_repository import SalaryRepository
from core.utils.dates import DateUtils
from core.utils.money_values import normalize_amount


class SalaryService:
    """Сервис для работы с зарплатами"""
    
    @staticmethod
    def add_salary(
        year: int,
        month: int,
        advance: float,
        salary: float,
        advance_date: Optional[str] = None,
        salary_date: Optional[str] = None
    ) -> Salary:
        """
        Добавить или обновить запись о зарплате.
        
        Args:
            year: Год
            month: Месяц (1-12)
            advance: Сумма аванса
            salary: Сумма зарплаты
            advance_date: Дата получения аванса (строка в формате ДД.ММ.ГГГГ)
            salary_date: Дата получения зарплаты (строка в формате ДД.ММ.ГГГГ)
            
        Returns:
            Salary: Созданная или обновленная запись
            
        Raises:
            ValueError: При неверном формате даты

        Примечание:
            Если запись за указанный месяц уже существует, она обновляется.
            Если не существует - создается новая запись.

        Даты выплат при обновлении существующей записи:
            - None — дата не передана, сохранённая остаётся
              (бот при ответе «-», API-запрос без поля даты);
            - пустая строка — дата очищена в форме и стирается
              (формы desktop и web подставляют сохранённые даты в поля);
            - ДД.ММ.ГГГГ — дата заменяется.
        """
        year, month = SalaryService._validate_period(year, month)
        advance = normalize_amount(advance, "сумма аванса")
        salary = normalize_amount(salary, "сумма зарплаты")

        new_salary = Salary(
            year=year,
            month=month,
            advance=advance,
            salary=salary,
            advance_date=SalaryService._parse_date_strict(advance_date, "даты аванса"),
            salary_date=SalaryService._parse_date_strict(salary_date, "даты зарплаты"),
        )
        return SalaryRepository.upsert(
            new_salary,
            keep_advance_date=advance_date is None,
            keep_salary_date=salary_date is None,
        )

    @staticmethod
    def _validate_period(year: Any, month: Any) -> tuple[int, int]:
        try:
            normalized_year = int(str(year).strip())
            normalized_month = int(str(month).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError("Год и месяц должны быть целыми числами") from exc

        if str(normalized_year) != str(year).strip():
            raise ValueError("Год должен быть целым числом")
        if str(normalized_month) != str(month).strip():
            raise ValueError("Месяц должен быть целым числом")
        if not 2000 <= normalized_year <= 2100:
            raise ValueError("Год должен быть в диапазоне 2000-2100")
        if not 1 <= normalized_month <= 12:
            raise ValueError("Месяц должен быть в диапазоне 1-12")
        return normalized_year, normalized_month
    
    @staticmethod
    def get_salary(year: int, month: int) -> Optional[Salary]:
        """Получить зарплату за конкретный месяц"""
        return SalaryRepository.get_by_year_month(year, month)
    
    @staticmethod
    def get_all_salaries() -> List[Salary]:
        """Получить все записи о зарплатах (упорядоченные по дате)"""
        return SalaryRepository.get_all()
    
    @staticmethod
    def get_salaries_by_year(year: int) -> List[Salary]:
        """Получить все записи за указанный год"""
        return SalaryRepository.get_by_year(year)
    
    @staticmethod
    def get_years() -> List[int]:
        """Получить список лет с данными (уникальные года)"""
        return SalaryRepository.get_years()
    
    @staticmethod
    def get_year_summary(year: int) -> YearSummary:
        """Получить сводку по году (суммы, средние значения)"""
        return SalaryRepository.get_year_summary(year)
    
    @staticmethod
    def get_all_years_summary() -> List[YearSummary]:
        """Получить сводку по всем годам"""
        return SalaryRepository.get_all_years_summary()
    
    @staticmethod
    def delete_salary(year: int, month: int) -> bool:
        """Удалить запись о зарплате за указанный месяц"""
        return SalaryRepository.delete_by_year_month(year, month)
    
    @staticmethod
    def delete_year(year: int) -> bool:
        """
        Удалить все записи за указанный год.

        Args:
            year: Год для удаления

        Returns:
            bool: True при успешном выполнении операции

        Примечание:
            Удаление выполняется одним атомарным запросом (см. delete_by_year).
            Возможные ошибки доступа к данным обрабатываются на уровне API.
        """
        SalaryRepository.delete_by_year(year)
        return True
    
    @staticmethod
    def get_next_month(year: int, month: int) -> tuple[int, int]:
        """Получить следующий месяц (для навигации)"""
        if month == 12:
            return year + 1, 1
        else:
            return year, month + 1
    
    @staticmethod
    def get_previous_month(year: int, month: int) -> tuple[int, int]:
        """Получить предыдущий месяц (для навигации)"""
        if month == 1:
            return year - 1, 12
        else:
            return year, month - 1
    
    @staticmethod
    def get_current_period() -> tuple[int, int]:
        """Получить текущий год и месяц (на основе системной даты)"""
        now = datetime.now()
        return now.year, now.month

    @staticmethod
    def _parse_date_strict(value: Optional[str], field_label: str) -> Optional[datetime]:
        """
        Строгий парсинг даты из строки.
        
        Args:
            value: Строка с датой
            field_label: Название поля для сообщения об ошибке
            
        Returns:
            Optional[datetime]: Объект datetime или None (для None и пустой строки)

        Raises:
            ValueError: При неверном формате даты
        """
        if value is None or not str(value).strip():
            return None
        normalized = SalaryService._normalize_date_input(value)
        if not normalized:
            raise ValueError(f"Неверный формат {field_label}. Ожидается ДД.ММ.ГГГГ")
        try:
            return datetime.strptime(normalized, "%d.%m.%Y")
        except ValueError:
            raise ValueError(f"Неверная дата {field_label}. Ожидается ДД.ММ.ГГГГ")

    @staticmethod
    def _normalize_date_input(value: str) -> Optional[str]:
        """
        Нормализация строки с датой.
        
        Поддерживает форматы:
        - "01012025" -> "01.01.2025"
        - "01.01.2025" -> "01.01.2025"
        - "01/01/2025" -> "01.01.2025"
        
        Args:
            value: Строка с датой
            
        Returns:
            Optional[str]: Нормализованная строка в формате ДД.ММ.ГГГГ или None
        """
        cleaned = value.strip()
        if not cleaned:
            return None
        # Извлекаем только цифры
        digits = "".join(ch for ch in cleaned if ch.isdigit())
        if len(digits) == 8:
            # Формат "01012025"
            return f"{digits[0:2]}.{digits[2:4]}.{digits[4:8]}"
        if len(cleaned) == 10 and cleaned[2] in "./-" and cleaned[5] in "./-":
            # Форматы "01.01.2025", "01/01/2025", "01-01-2025"
            return f"{cleaned[0:2]}.{cleaned[3:5]}.{cleaned[6:10]}"
        return None
    
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """Получить статистику по всем данным"""
        return SalaryRepository.get_statistics()
    
    @staticmethod
    def get_monthly_series_dto(year: Optional[int] = None) -> Dict[str, Any]:
        """
        Получить DTO для построения месячного графика.
        
        Args:
            year: Год или None для всех данных
            
        Returns:
            Dict: Структура данных для графика (без форматирования для chart)
        """
        # Получаем данные за год или все данные
        if year:
            salaries = SalaryRepository.get_by_year(year)
        else:
            salaries = SalaryRepository.get_all()

        # Сортируем по году и месяцу
        salaries = sorted(salaries, key=lambda s: (s.year, s.month))
        
        # Формируем структуру для фронтенда
        items = []
        for salary in salaries:
            items.append({
                "year": int(salary.year),
                "month": int(salary.month),
                "advance": float(salary.advance),
                "salary": float(salary.salary),
                "total": float(salary.total)
            })

        return {
            "period": "year" if year else "all",
            "year": year,
            "items": items
        }

    @staticmethod
    def get_year_with_all_months(year: int) -> Dict[str, Any]:
        """
        Получить данные за год с заполнением всех 12 месяцев.
        
        Для месяцев без данных создаются записи с нулевыми значениями.
        Это обеспечивает корректное отображение всех месяцев в интерфейсе.
        
        Args:
            year: Год
            
        Returns:
            Dict: Данные года с полной структурой месяцев
        """
        # Получаем существующие записи за год
        existing_salaries = SalaryRepository.get_by_year(year)
        # Преобразуем в словарь для удобства: месяц -> запись
        existing_by_month = {s.month: s for s in existing_salaries}
        
        # Создаем список всех месяцев (1-12)
        all_months = []
        for month in range(1, 13):
            if month in existing_by_month:
                # Месяц с данными
                salary = existing_by_month[month]
                salary_dict = salary.to_dict()
                all_months.append({
                    'month': month,
                    'month_name': salary.month_name,
                    'advance': salary.advance,
                    'salary': salary.salary,
                    'total': salary.total,
                    'advance_date': salary_dict.get('advance_date', ''),
                    'salary_date': salary_dict.get('salary_date', ''),
                    'has_data': True
                })
            else:
                # Месяц без данных (заполнитель)
                all_months.append({
                    'month': month,
                    'month_name': DateUtils.get_month_name(month),
                    'advance': 0.0,
                    'salary': 0.0,
                    'total': 0.0,
                    'advance_date': '',
                    'salary_date': '',
                    'has_data': False
                })
        
        # Создаем сводку по году
        summary = SalaryRepository.get_year_summary(year)
        
        return {
            'year': year,
            'summary': {
                'year': summary.year,
                'total_advance': summary.total_advance,
                'total_salary': summary.total_salary,
                'total': summary.total,
                'average_monthly': summary.average_monthly,
                'months_with_data': len(existing_salaries)
            },
            'months': all_months
        }
    
    @staticmethod
    def get_all_grouped_by_year() -> List[Dict[str, Any]]:
        """
        Получить все данные, сгруппированные по годам.
        
        Returns:
            List[Dict]: Список годов с полной структурой месяцев
        """
        years = SalaryRepository.get_years()
        result = []
        for year in years:
            result.append(SalaryService.get_year_with_all_months(year))
        return result

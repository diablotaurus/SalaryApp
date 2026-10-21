"""
Утилиты для работы с датами и временем.

Содержит методы для форматирования, парсинга и манипуляции с датами,
а также константы с названиями месяцев на русском языке.
"""

from datetime import datetime
from typing import List, Tuple


class DateUtils:
    """Утилиты для работы с датами и временем"""
    
    # Полные названия месяцев на русском языке
    MONTH_NAMES = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    # Сокращенные названия месяцев на русском языке
    MONTH_NAMES_SHORT = [
        "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
        "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"
    ]
    
    @staticmethod
    def get_month_name(month: int, short: bool = False) -> str:
        """
        Получить название месяца по его номеру.
        
        Args:
            month: Номер месяца (1-12)
            short: Если True, вернуть сокращенное название
            
        Returns:
            str: Название месяца или пустая строка при неверном номере
            
        Примеры:
            get_month_name(1) -> "Январь"
            get_month_name(1, short=True) -> "Янв"
        """
        if 1 <= month <= 12:
            if short:
                return DateUtils.MONTH_NAMES_SHORT[month - 1]
            return DateUtils.MONTH_NAMES[month - 1]
        return ""
    
    @staticmethod
    def get_month_number(month_name: str) -> int:
        """
        Получить номер месяца по его названию.
        
        Args:
            month_name: Название месяца (полное или в любом регистре)
            
        Returns:
            int: Номер месяца (1-12) или 0 если название не найдено
            
        Пример:
            get_month_number("Январь") -> 1
            get_month_number("январь") -> 1
        """
        month_name_lower = month_name.lower()
        for i, name in enumerate(DateUtils.MONTH_NAMES, 1):
            if name.lower() == month_name_lower:
                return i
        return 0
    
    @staticmethod
    def get_current_period() -> Tuple[int, int]:
        """
        Получить текущий год и месяц.

        Returns:
            Tuple[int, int]: (текущий год, текущий месяц)

        Использование:
            - Для предзаполнения форм ввода даты
            - Для фильтрации данных по текущему периоду
        """
        now = datetime.now()
        return now.year, now.month
    
    @staticmethod
    def get_next_month(year: int, month: int) -> Tuple[int, int]:
        """
        Получить следующий месяц.
        
        Args:
            year: Текущий год
            month: Текущий месяц (1-12)
            
        Returns:
            Tuple[int, int]: (год следующего месяца, номер следующего месяца)
            
        Пример:
            get_next_month(2024, 12) -> (2025, 1)
            get_next_month(2024, 5) -> (2024, 6)
        """
        if month == 12:
            return year + 1, 1
        return year, month + 1
    
    @staticmethod
    def get_previous_month(year: int, month: int) -> Tuple[int, int]:
        """
        Получить предыдущий месяц.
        
        Args:
            year: Текущий год
            month: Текущий месяц (1-12)
            
        Returns:
            Tuple[int, int]: (год предыдущего месяца, номер предыдущего месяца)
            
        Пример:
            get_previous_month(2024, 1) -> (2023, 12)
            get_previous_month(2024, 5) -> (2024, 4)
        """
        if month == 1:
            return year - 1, 12
        return year, month - 1
    
    @staticmethod
    def get_months_list() -> List[Tuple[int, str]]:
        """
        Получить список всех месяцев с номерами и названиями.
        
        Returns:
            List[Tuple[int, str]]: Список кортежей (номер месяца, название)
            
        Пример:
            [(1, "Январь"), (2, "Февраль"), ..., (12, "Декабрь")]
        """
        return [(i, DateUtils.MONTH_NAMES[i-1]) for i in range(1, 13)]
    
    @staticmethod
    def format_date(date: datetime, format_str: str = "%d.%m.%Y") -> str:
        """
        Форматировать дату в строку.
        
        Args:
            date: Объект datetime для форматирования
            format_str: Строка формата (по умолчанию "день.месяц.год")
            
        Returns:
            str: Отформатированная дата
            
        Пример:
            format_date(datetime(2024, 1, 15)) -> "15.01.2024"
        """
        return date.strftime(format_str)
    
    @staticmethod
    def parse_date(date_str: str, format_str: str = "%d.%m.%Y") -> datetime:
        """
        Разобрать строку в объект datetime.
        
        Args:
            date_str: Строка с датой
            format_str: Ожидаемый формат строки (по умолчанию "день.месяц.год")
            
        Returns:
            datetime: Объект datetime
            
        Raises:
            ValueError: Если строка не соответствует формату
            
        Пример:
            parse_date("15.01.2024") -> datetime(2024, 1, 15)
        """
        return datetime.strptime(date_str, format_str)
    
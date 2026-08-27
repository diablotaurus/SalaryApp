"""
Утилиты для работы с денежными суммами.

Содержит методы для форматирования, парсинга и вычислений
с денежными суммами с поддержкой различных валют.
"""

from typing import Union
from core.config.settings import config


class MoneyUtils:
    """Утилиты для форматирования и вычислений с денежными суммами"""
    
    @staticmethod
    def format_amount(amount: Union[float, int], currency: str = None) -> str:
        """
        Форматировать сумму с валютой.
        
        Args:
            amount: Сумма для форматирования
            currency: Валюта (если None, берется из настроек)
            
        Returns:
            str: Отформатированная строка (например: "12 345.67 руб.")
            
        Форматирование:
            - Разделитель тысяч: пробел
            - Разделитель дробной части: точка
            - Два знака после запятой
            - Валюта добавляется справа
            
        Примеры:
            format_amount(12345.67) -> "12 345.67 руб."
            format_amount(12345.67, "$") -> "12 345.67 $"
        """
        if currency is None:
            currency = config.app.currency
        
        # Форматирование числа с разделителями тысяч
        formatted = f"{amount:,.2f}".replace(',', ' ')
        
        # Добавление валюты если указана
        if currency:
            formatted = f"{formatted} {currency}"
        
        return formatted

    @staticmethod
    def format_amount_plain(amount: Union[float, int]) -> str:
        """
        Форматировать сумму без валюты.
        
        Args:
            amount: Сумма для форматирования
            
        Returns:
            str: Отформатированная строка (например: "12 345.67")
            
        Использование:
            - Для внутренних вычислений
            - Для отображения в таблицах где валюта указана в заголовке
        """
        return f"{amount:,.2f}".replace(",", " ")

    @staticmethod
    def format_kpi_amount(amount: Union[float, int], currency: str = None) -> str:
        """
        Форматировать сумму для KPI (ключевых показателей).
        
        Args:
            amount: Сумма для форматирования
            currency: Валюта (если None, берется из настроек)
            
        Returns:
            str: Отформатированная строка с валютой
            
        Отличие от format_amount:
            - Алиас для единообразия кода
            - Может быть расширен для специального форматирования KPI
        """
        return MoneyUtils.format_amount(amount, currency)
    
    @staticmethod
    def parse_amount(amount_str: str) -> float:
        """
        Разобрать сумму из строки.
        
        Args:
            amount_str: Строка с суммой (может содержать пробелы, запятые)
            
        Returns:
            float: Числовое значение суммы или 0.0 при ошибке
            
        Поддержка форматов:
            - "12345.67" -> 12345.67
            - "12 345.67" -> 12345.67
            - "12,345.67" -> 12345.67
            - "12345,67" -> 12345.67
            
        Безопасность:
            - Обработка ValueError и AttributeError
            - Возврат 0.0 вместо выброса исключения
        """
        try:
            # Очистка строки: удаление пробелов и замена запятых на точки
            cleaned = amount_str.strip().replace(' ', '').replace(',', '.')
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0
    
    @staticmethod
    def calculate_total(advance: float, salary: float) -> float:
        """
        Рассчитать общую сумму (аванс + зарплата).
        
        Args:
            advance: Сумма аванса
            salary: Сумма зарплаты
            
        Returns:
            float: Общая сумма
            
        Пример:
            calculate_total(10000, 20000) -> 30000.0
        """
        return advance + salary
    
    @staticmethod
    def calculate_average(amounts: list) -> float:
        """
        Рассчитать среднее значение списка сумм.
        
        Args:
            amounts: Список сумм
            
        Returns:
            float: Среднее значение или 0.0 если список пуст
            
        Особенности:
            - Защита от деления на ноль
            - Работает с пустым списком
        """
        if not amounts:
            return 0.0
        return sum(amounts) / len(amounts)
    
    @staticmethod
    def calculate_growth(current: float, previous: float) -> float:
        """
        Рассчитать темп роста в процентах.
        
        Args:
            current: Текущее значение
            previous: Предыдущее значение
            
        Returns:
            float: Темп роста в процентах (может быть отрицательным)
            
        Формула:
            ((current - previous) / previous) * 100
            
        Особенности:
            - При previous = 0 возвращает 0.0 (избегание деления на ноль)
            - Отрицательное значение означает снижение
        """
        if previous == 0:
            return 0.0
        return ((current - previous) / previous) * 100

"""
Сервис для статистических вычислений.

Содержит методы для расчета различных статистических показателей
по данным о зарплатах, включая сравнения по годам, темпы роста,
средние значения и поиск лучших периодов.
"""

from collections import defaultdict
from typing import Dict, Any, Iterable, List, Optional
from datetime import datetime
from core.models.year import calculate_average_monthly, is_payment_complete
from core.repositories.analytics_repository import AnalyticsRepository
from core.repositories.salary_repository import SalaryRepository
from core.utils.clock import moscow_now
from core.utils.dates import DateUtils


# Сравнение месяца со средним: окно и минимум месяцев, при котором сравнение осмысленно
RECENT_MONTHS = 12
MIN_MONTHS_TO_COMPARE = 3
TOP_MONTHS = 3


class StatisticsService:
    """Сервис для вычисления статистики по данным о зарплатах"""

    @staticmethod
    def percent_change(current: float, previous: float) -> Optional[float]:
        """Изменение в процентах; None, если сравнивать не с чем (предыдущее значение 0)."""
        if not previous:
            return None
        return (float(current) / float(previous) - 1) * 100

    @staticmethod
    def compare_with_recent_average(year: int, month: int, now: datetime | None = None) -> Optional[Dict[str, Any]]:
        """
        Сравнить сумму месяца со средним за предыдущие RECENT_MONTHS месяцев.

        Учитываются только месяцы с фактически выплаченной зарплатой — то же
        правило, что у «Среднемесячно» (is_payment_complete). None, если сам
        месяц ещё не выплачен целиком или для сравнения мало данных.
        """
        now = now or moscow_now()
        records = SalaryRepository.get_all()
        target = next((r for r in records if (r.year, r.month) == (year, month)), None)
        if target is None or not is_payment_complete(target, now):
            return None

        index = year * 12 + month
        previous = [
            record for record in records
            if 0 < index - (record.year * 12 + record.month) <= RECENT_MONTHS
            and is_payment_complete(record, now)
        ]
        if len(previous) < MIN_MONTHS_TO_COMPARE:
            return None

        average = sum(record.total for record in previous) / len(previous)
        return {
            "total": target.total,
            "average": average,
            "percent": StatisticsService.percent_change(target.total, average),
            "months": len(previous),
        }

    @staticmethod
    def calculate_average_monthly_from_records(records: Iterable[Any], now: datetime | None = None) -> float:
        """
        Рассчитать среднемесячное значение по записям.

        Правило:
        - месяц учитывается только если зарплата за него фактически выплачена;
        - выплата подтверждается salary > 0 и:
          1) salary_date задана и наступила (<= now), либо
          2) salary_date не задана (legacy-данные), но месяц строго раньше текущего.

        Args:
            records: Итерируемая коллекция объектов с полями year, month, advance, salary
            now: Текущая дата (для тестирования можно передать вручную)

        Returns:
            float: Среднемесячное значение
        """
        return calculate_average_monthly(records, now)
    
    @staticmethod
    def compare_year_to_date(year: int, now: datetime | None = None) -> Optional[Dict[str, Any]]:
        """
        Год к году за одинаковый период: январь — последний выплаченный месяц года.

        Последний месяц берётся по правилу is_payment_complete: месяц, где
        пока пришёл только аванс, не занижает сравнение. None — если в году
        нет выплаченных месяцев или нет данных за тот же период прошлого года.
        """
        now = now or moscow_now()
        records = SalaryRepository.get_all()
        this_year = [record for record in records if record.year == year]
        paid_months = [record.month for record in this_year if is_payment_complete(record, now)]
        if not paid_months:
            return None
        last_month = max(paid_months)
        previous = [record for record in records if record.year == year - 1 and record.month <= last_month]
        if not previous:
            return None
        total = sum(record.total for record in this_year if record.month <= last_month)
        previous_total = sum(record.total for record in previous)
        return {
            "year": year,
            "last_month": last_month,
            "total": total,
            "previous_total": previous_total,
            "percent": StatisticsService.percent_change(total, previous_total),
        }

    @staticmethod
    def get_records() -> Dict[str, Any]:
        """
        Рекорды за всё время: лучшие месяцы, лучший год по сумме и по среднемесячному.

        Лучший год по сумме выбирается среди полных лет (12 месяцев), чтобы
        неполный текущий год не проигрывал заведомо; если полных лет нет — среди всех.
        По среднемесячному сравнимы и неполные годы (правило is_payment_complete).
        """
        records = SalaryRepository.get_all()
        top_months = [
            {"year": record.year, "month": record.month,
             "month_name": DateUtils.get_month_name(record.month), "total": record.total}
            for record in sorted(records, key=lambda item: (item.total, item.year, item.month), reverse=True)
            if record.total > 0
        ][:TOP_MONTHS]

        totals = AnalyticsRepository.get_yearly_totals()
        full_years = [item for item in totals if int(item["months_count"] or 0) >= 12] or totals
        best_year = max(full_years, key=lambda item: float(item["total"] or 0), default=None)

        by_year: Dict[int, List[Any]] = defaultdict(list)
        for record in records:
            by_year[record.year].append(record)
        averages = {year: calculate_average_monthly(items) for year, items in by_year.items()}
        best_average = max(averages.items(), key=lambda item: item[1], default=None)

        return {
            "top_months": top_months,
            "best_year": (
                {"year": int(best_year["year"]), "total": float(best_year["total"] or 0)} if best_year else None
            ),
            "best_average_year": (
                {"year": best_average[0], "average": best_average[1]}
                if best_average and best_average[1] > 0 else None
            ),
        }

    @staticmethod
    def get_yearly_comparison_dto() -> Dict[str, Any]:
        """
        Получить DTO (Data Transfer Object) для сравнения по годам.
        
        Returns:
            Dict[str, Any]: Структура с данными для графика сравнения по годам
            
        Данные:
            - year: Год
            - total: Общая сумма за год
            
        Производительность:
            - Один агрегирующий SQL-запрос (AnalyticsRepository.get_yearly_totals)
            - Данные возвращаются в формате, готовом для использования в графиках
        """
        yearly_totals = AnalyticsRepository.get_yearly_totals()
        items = []
        for item in yearly_totals:
            items.append({
                "year": int(item["year"]),
                "total": float(item["total"] or 0)
            })
        return {"items": items}
    
    @staticmethod
    def get_growth_rate_dto() -> Dict[str, Any]:
        """
        Получить DTO для графика темпов роста.
        
        Returns:
            Dict[str, Any]: Структура с данными о росте доходов по годам
            
        Особенности:
            - Для неполных годов делается проекция на полный год
            - Поле 'projected' указывает, является ли значение спроектированным
            - Используется для отображения реалистичной динамики роста
            
        Проекция:
            - Если в году есть данные менее чем за 12 месяцев, 
              общая сумма проецируется на 12 месяцев
            - Это дает более точное сравнение между годами
        """
        rows = AnalyticsRepository.get_yearly_totals(ascending=True)
        
        items = []
        for row in rows:
            total = float(row["total"] or 0)
            months_count = int(row["months_count"] or 0)
            
            # Определение, является ли год неполным (данные менее чем за 12 месяцев)
            projected = months_count > 0 and months_count < 12
            
            # Проекция неполных годов на 12 месяцев для корректного сравнения
            if projected:
                adjusted_total = (total / months_count) * 12
            else:
                adjusted_total = total
                
            items.append({
                "year": int(row["year"]),
                "total": adjusted_total,
                "projected": projected  # Флаг спроектированных данных
            })
        return {"items": items}
    
    @staticmethod
    def get_average_by_month_dto() -> Dict[str, Any]:
        """
        Получить DTO для графика средних значений по месяцам.
        
        Returns:
            Dict[str, Any]: Структура со средними значениями по месяцам
            
        Данные:
            - month: Номер месяца (1-12)
            - avg_advance: Средний аванс за месяц
            - avg_salary: Средняя зарплата за месяц
            - avg_total: Средняя общая сумма за месяц
            
        Использование:
            - Полезно для выявления сезонных тенденций
            - Помогает планировать бюджет по месяцам

        Учитываются только месяцы с фактически выплаченной зарплатой — то же
        правило, что у KPI «Среднемесячно» (is_payment_complete): месяц,
        где пока есть только аванс, не занижает среднее.
        """
        now = moscow_now()
        paid_by_month: Dict[int, List[Any]] = defaultdict(list)
        for record in SalaryRepository.get_all():
            if is_payment_complete(record, now):
                paid_by_month[int(record.month)].append(record)

        items = []
        for month in sorted(paid_by_month):
            records = paid_by_month[month]
            count = len(records)
            items.append({
                "month": month,
                "avg_advance": sum(record.advance for record in records) / count,
                "avg_salary": sum(record.salary for record in records) / count,
                "avg_total": sum(record.total for record in records) / count,
            })
        return {"items": items}
    
    @staticmethod
    def get_best_periods() -> Dict[str, Any]:
        """
        Найти лучший месяц и лучший год по общей сумме дохода.
        
        Returns:
            Dict[str, Any]: Информация о лучшем месяце и лучшем годе
            
        Критерии:
            - Лучший месяц: месяц с максимальной суммой (аванс + зарплата)
            - Лучший год: год с максимальной общей суммой
            
        Структура результата:
            - best_month: Словарь с данными о лучшем месяце или None
            - best_year: Словарь с данными о лучшем годе или None
        """
        best_month = AnalyticsRepository.get_best_month()
        best_year = AnalyticsRepository.get_best_year()
        
        # Инициализация результата
        result = {"best_month": None, "best_year": None}
        
        # Заполнение данных о лучшем месяце если найден
        if best_month:
            result["best_month"] = {
                "year": best_month["year"],
                "month": best_month["month"],
                "month_name": DateUtils.get_month_name(best_month["month"]),
                "total": float(best_month["total"] or 0)
            }
        
        # Заполнение данных о лучшем годе если найден
        if best_year:
            result["best_year"] = {
                "year": best_year["year"],
                "total": float(best_year["total"] or 0)
            }
        
        return result
    
    @staticmethod
    def get_summary_statistics(year: int = None) -> Dict[str, Any]:
        """
        Получить сводную статистику по всем данным или за конкретный год.
        
        Args:
            year: Опциональный параметр - год для фильтрации статистики
            
        Returns:
            Dict[str, Any]: Словарь со сводной статистикой
            
        Статистические показатели:
            - Общие суммы (авансы, зарплаты, итого)
            - Средние месячные значения
            - Количество записей и лет
            - Первый и последний год с данными
            
        Особенности:
            - При year=None возвращает статистику за все время
            - При указанном year - статистику только за этот год
        """
        # Получение базовой статистики из репозитория
        stats = SalaryRepository.get_statistics(year)
        records = SalaryRepository.get_by_year(year) if year is not None else SalaryRepository.get_all()
        
        # Извлечение и преобразование базовых показателей
        total_records = stats.get("total_records", 0) or 0
        total_advance = float(stats.get("total_advance_all", 0) or 0)
        total_salary = float(stats.get("total_salary_all", 0) or 0)
        
        # Определение первого и последнего года
        if year is not None:
            # Для конкретного года первый и последний год совпадают
            first_year = year
            last_year = year
        else:
            # Для общей статистики берем из данных (без данных — текущий год по МСК)
            current_year = moscow_now().year
            first_year = stats.get("first_year") or current_year
            last_year = stats.get("last_year") or current_year
        
        # Дополнительные расчеты
        years_count = len(stats.get("by_year", []))
        total_amount = total_advance + total_salary
        
        # Формирование сводки
        summary = {
            "total_records": total_records,
            "total_advance": total_advance,
            "total_salary": total_salary,
            "first_year": first_year,
            "last_year": last_year,
            "years_count": years_count,
            "total_amount": total_amount
        }
        
        # Расчет средних значений (если есть записи)
        if summary["total_records"] > 0:
            summary["avg_monthly_advance"] = summary["total_advance"] / summary["total_records"]
            summary["avg_monthly_salary"] = summary["total_salary"] / summary["total_records"]
        else:
            # Если записей нет - нулевые значения
            summary["avg_monthly_advance"] = 0
            summary["avg_monthly_salary"] = 0

        # Единое бизнес-правило среднемесячного для всех интерфейсов
        summary["avg_monthly_total"] = StatisticsService.calculate_average_monthly_from_records(records)

        # Дополнительные поля для совместимости
        summary["total_all"] = summary["total_amount"]
        summary["average_monthly"] = summary["avg_monthly_total"]
        
        return summary

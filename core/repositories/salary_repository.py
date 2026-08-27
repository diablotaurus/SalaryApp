"""
Репозиторий для работы с данными о зарплатах.

Реализует паттерн Repository для абстракции доступа к данным.
Содержит CRUD-операции и специализированные запросы для работы с зарплатами.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from core.database.connection import DatabaseConnection
from core.models.salary import Salary
from core.models.year import YearSummary
from core.repositories.analytics_repository import AnalyticsRepository
from core.utils.money_values import from_cents, to_cents


class SalaryRepository:
    """Репозиторий для работы с таблицей зарплат в базе данных"""
    
    @staticmethod
    def save(salary: Salary) -> Salary:
        """
        Сохранить запись о зарплате (INSERT или UPDATE).
        
        Args:
            salary: Объект Salary для сохранения
            
        Returns:
            Salary: Сохраненный объект с заполненным ID (при INSERT)
            
        Безопасность:
            - Все значения передаются через параметризованные запросы
            - Предотвращение SQL-инъекций гарантируется на уровне драйвера SQLite
            - Уникальность пары (year, month) обеспечивается бизнес-логикой
              в SalaryService.add_salary (поиск существующей записи перед вставкой)
            
        Производительность:
            - Используется UPSERT (INSERT OR UPDATE) через отдельные запросы
            - Можно оптимизировать через INSERT OR REPLACE, но нужно сохранить created_at
        """
        if not salary.id:
            return SalaryRepository.upsert(salary)

        conn = DatabaseConnection.get_connection()
        advance_date = (
            salary.advance_date.date().isoformat() if salary.advance_date else None
        )
        salary_date = (
            salary.salary_date.date().isoformat() if salary.salary_date else None
        )
        cursor = conn.execute(
            """
            UPDATE salaries
            SET year = ?, month = ?, advance = ?, salary = ?,
                advance_date = ?, salary_date = ?
            WHERE id = ?
            RETURNING *
            """,
            (
                salary.year,
                salary.month,
                to_cents(salary.advance),
                to_cents(salary.salary),
                advance_date,
                salary_date,
                salary.id,
            ),
        )
        row = cursor.fetchone()
        conn.commit()
        return SalaryRepository._row_to_salary(row) if row else salary

    @staticmethod
    def upsert(salary: Salary) -> Salary:
        """Atomically insert or update the unique year/month record."""
        conn = DatabaseConnection.get_connection()
        advance_date = (
            salary.advance_date.date().isoformat() if salary.advance_date else None
        )
        salary_date = (
            salary.salary_date.date().isoformat() if salary.salary_date else None
        )
        cursor = conn.execute(
            """
            INSERT INTO salaries (
                year, month, advance, salary, advance_date, salary_date
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(year, month) DO UPDATE SET
                advance = excluded.advance,
                salary = excluded.salary,
                advance_date = COALESCE(excluded.advance_date, salaries.advance_date),
                salary_date = COALESCE(excluded.salary_date, salaries.salary_date)
            RETURNING *
            """,
            (
                salary.year,
                salary.month,
                to_cents(salary.advance),
                to_cents(salary.salary),
                advance_date,
                salary_date,
            ),
        )
        row = cursor.fetchone()
        conn.commit()
        return SalaryRepository._row_to_salary(row)
    
    @staticmethod
    def get_by_id(salary_id: int) -> Optional[Salary]:
        """
        Получить запись о зарплате по ID.
        
        Args:
            salary_id: Идентификатор записи
            
        Returns:
            Optional[Salary]: Объект Salary или None, если не найден
            
        Производительность:
            - Поиск по PRIMARY KEY - максимально быстрая операция в SQLite
            - Не требует дополнительных индексов
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            "SELECT * FROM salaries WHERE id = ?", 
            (salary_id,)
        )
        row = cursor.fetchone()
        return SalaryRepository._row_to_salary(row) if row else None
    
    @staticmethod
    def get_by_year_month(year: int, month: int) -> Optional[Salary]:
        """
        Получить запись о зарплате по году и месяцу.
        
        Args:
            year: Год
            month: Месяц (1-12)
            
        Returns:
            Optional[Salary]: Объект Salary или None
            
        Производительность:
            - Рекомендуется составной индекс (year, month)
            - В текущей реализации используется индекс idx_salaries_year
            - Можно добавить индекс idx_salaries_year_month для оптимизации
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            "SELECT * FROM salaries WHERE year = ? AND month = ?", 
            (year, month)
        )
        row = cursor.fetchone()
        return SalaryRepository._row_to_salary(row) if row else None
    
    @staticmethod
    def get_all() -> List[Salary]:
        """
        Получить все записи о зарплатах.
        
        Returns:
            List[Salary]: Список всех записей, отсортированных по дате
            
        Внимание:
            - Метод может быть медленным при большом количестве записей (1000+)
            - Для production-использования рекомендуется пагинация или лимиты
            - Сортировка по year DESC, month DESC - новые записи сверху
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            "SELECT * FROM salaries ORDER BY year DESC, month DESC"
        )
        return [SalaryRepository._row_to_salary(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_by_year(year: int) -> List[Salary]:
        """
        Получить все записи за конкретный год.
        
        Args:
            year: Год для фильтрации
            
        Returns:
            List[Salary]: Список записей за год, отсортированных по месяцам
            
        Производительность:
            - Использует индекс idx_salaries_year
            - Сортировка по month DESC - последние месяцы сверху
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            "SELECT * FROM salaries WHERE year = ? ORDER BY month DESC",
            (year,)
        )
        return [SalaryRepository._row_to_salary(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_years() -> List[int]:
        """
        Получить список уникальных лет, за которые есть данные.
        
        Returns:
            List[int]: Отсортированный по убыванию список годов
            
        Производительность:
            - DISTINCT + ORDER BY может быть дорогой операцией
            - Индекс idx_salaries_year ускоряет выполнение
            - Для больших таблиц можно кэшировать результат
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            "SELECT DISTINCT year FROM salaries ORDER BY year DESC"
        )
        return [row['year'] for row in cursor.fetchall()]
    
    @staticmethod
    def get_year_summary(year: int) -> YearSummary:
        """
        Получить агрегированную сводку за год.
        
        Args:
            year: Год для анализа
            
        Returns:
            YearSummary: Объект с суммарными показателями и детализацией
            
        Бизнес-логика:
            - Считает суммы авансов, зарплат и общую сумму
            - Включает количество записей (месяцев с данными)
            - Предоставляет детализацию по каждому месяцу
            
        Производительность:
            - Использует агрегатные функции SQL (SUM, COUNT)
            - Два запроса: один для агрегации, второй для деталей
            - Можно объединить в один запрос с GROUP BY и JOIN, но сложнее читать
        """
        records = SalaryRepository.get_by_year(year)
        year_summary = YearSummary(
            year=year,
            total_advance=sum(record.advance for record in records),
            total_salary=sum(record.salary for record in records),
            records=records
        )
        
        # Заполнение деталей по месяцам
        for salary in records:
            year_summary.month_details[salary.month] = salary.to_dict()
        
        return year_summary

    @staticmethod
    def get_connection():
        """
        Получить соединение с БД (служебный метод).
        
        Returns:
            Connection: Активное соединение с базой данных
            
        Примечание:
            - В основном используется для миграций и тестов
            - В обычной работе использовать DatabaseConnection.get_connection()
        """
        from core.database.connection import DatabaseConnection
        return DatabaseConnection.get_connection()

    @staticmethod
    def delete_by_id(salary_id: int) -> bool:
        """
        Удалить запись по ID.
        
        Args:
            salary_id: Идентификатор удаляемой записи
            
        Returns:
            bool: True если запись удалена, False если не найдена
            
        Безопасность:
            - Удаление только по ID гарантирует точность операции
            - Нельзя случайно удалить несколько записей
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            "DELETE FROM salaries WHERE id = ?", 
            (salary_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    
    @staticmethod
    def delete_by_year_month(year: int, month: int) -> bool:
        """
        Удалить запись по году и месяцу.
        
        Args:
            year: Год
            month: Месяц
            
        Returns:
            bool: True если запись удалена
            
        Примечание:
            - Уникальность пары (year, month) гарантирует удаление максимум одной записи
            - Используется для обновления данных через удаление+вставку
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            "DELETE FROM salaries WHERE year = ? AND month = ?", 
            (year, month)
        )
        conn.commit()
        return cursor.rowcount > 0
    
    @staticmethod
    def delete_by_year(year: int) -> int:
        """
        Удалить все записи за указанный год одним запросом.

        Args:
            year: Год для удаления

        Returns:
            int: Количество удалённых записей

        Особенности:
            - Операция атомарна (один DELETE), частичного удаления быть не может
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            "DELETE FROM salaries WHERE year = ?",
            (year,)
        )
        conn.commit()
        return cursor.rowcount

    @staticmethod
    def get_statistics(year: Optional[int] = None) -> Dict[str, Any]:
        """
        Получить статистику по данным.
        
        Args:
            year: Опционально - год для фильтрации статистики
            
        Returns:
            Dict: Словарь со статистическими данными
            
        Статистика включает:
            - Общее количество записей
            - Суммы авансов и зарплат
            - Первый и последний год с данными
            - Разбивку по годам (только при year=None)
            
        Производительность:
            - Агрегатные функции работают эффективно с индексами
            - Для больших таблиц можно добавить материализованные представления
        """
        return AnalyticsRepository.get_statistics(year)
    
    @staticmethod
    def _row_to_salary(row) -> Salary:
        """
        Преобразовать строку из БД в объект Salary.
        
        Args:
            row: Строка результата SQL-запроса (sqlite3.Row)
            
        Returns:
            Salary: Объект Salary с заполненными полями
            
        Безопасность:
            - Проверка наличия колонок в результате запроса
            - Обработка NULL значений для дат
            - Преобразование строк в datetime объекты
        """
        # Проверяем наличие колонок в результате запроса
        has_advance_date = 'advance_date' in row.keys()
        has_salary_date = 'salary_date' in row.keys()
        
        # Создаем объект Salary с преобразованием типов
        return Salary(
            id=row['id'],
            year=row['year'],
            month=row['month'],
            advance=from_cents(row['advance']),
            salary=from_cents(row['salary']),
            # Преобразование строк дат в datetime объекты
            advance_date=datetime.fromisoformat(row['advance_date']) if has_advance_date and row['advance_date'] else None,
            salary_date=datetime.fromisoformat(row['salary_date']) if has_salary_date and row['salary_date'] else None,
            # created_at может быть NULL в старых записях
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )

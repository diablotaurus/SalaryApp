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
from core.utils.clock import parse_utc
from core.utils.money_values import from_cents, to_cents


class SalaryRepository:
    """Репозиторий для работы с таблицей зарплат в базе данных"""
    
    @staticmethod
    def save(salary: Salary) -> Salary:
        """
        Сохранить запись о зарплате.

        Args:
            salary: Объект Salary для сохранения

        Returns:
            Salary: Сохранённая запись в том виде, в каком она лежит в БД

        Поведение:
            - без id — атомарный upsert по паре (year, month), см. upsert();
            - с id — UPDATE этой записи (created_at не меняется).

        Безопасность:
            - Все значения передаются через параметризованные запросы
            - Уникальность пары (year, month) гарантирует ограничение UNIQUE в БД
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
                advance_date = ?, salary_date = ?, note = ?
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
                salary.note,
                salary.id,
            ),
        )
        row = cursor.fetchone()
        conn.commit()
        return SalaryRepository._row_to_salary(row) if row else salary

    @staticmethod
    def upsert(
        salary: Salary,
        *,
        keep_advance_date: bool = True,
        keep_salary_date: bool = True,
        keep_note: bool = True,
    ) -> Salary:
        """
        Атомарно вставить или обновить запись за год/месяц.

        Args:
            salary: Запись для сохранения
            keep_advance_date: При обновлении и пустой дате аванса оставить
                сохранённую дату (иначе пустая дата стирает её)
            keep_salary_date: То же для даты зарплаты
            keep_note: То же для заметки к месяцу
        """
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
                year, month, advance, salary, advance_date, salary_date, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(year, month) DO UPDATE SET
                advance = excluded.advance,
                salary = excluded.salary,
                advance_date = CASE WHEN ?
                    THEN COALESCE(excluded.advance_date, salaries.advance_date)
                    ELSE excluded.advance_date END,
                salary_date = CASE WHEN ?
                    THEN COALESCE(excluded.salary_date, salaries.salary_date)
                    ELSE excluded.salary_date END,
                note = CASE WHEN ?
                    THEN COALESCE(excluded.note, salaries.note)
                    ELSE excluded.note END
            RETURNING *
            """,
            (
                salary.year,
                salary.month,
                to_cents(salary.advance),
                to_cents(salary.salary),
                advance_date,
                salary_date,
                salary.note,
                keep_advance_date,
                keep_salary_date,
                keep_note,
            ),
        )
        cursor.fetchone()
        conn.commit()
        # Перечитать через month_totals: в итоге месяца — и его доп. выплаты
        return SalaryRepository.get_by_year_month(salary.year, salary.month)
    
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
            - Поиск идёт по уникальному индексу пары (year, month)
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            "SELECT * FROM month_totals WHERE year = ? AND month = ?",
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
            "SELECT * FROM month_totals ORDER BY year DESC, month DESC"
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
            "SELECT * FROM month_totals WHERE year = ? ORDER BY month DESC",
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
            records=records,
            total_extras=sum(record.extras_total for record in records),
        )
        
        # Заполнение деталей по месяцам
        for salary in records:
            year_summary.month_details[salary.month] = salary.to_dict()
        
        return year_summary

    @staticmethod
    def ensure_month(year: int, month: int) -> None:
        """Создать пустую запись месяца (0/0), если её нет — для доп. выплаты без аванса."""
        conn = DatabaseConnection.get_connection()
        conn.execute("INSERT OR IGNORE INTO salaries (year, month) VALUES (?, ?)", (year, month))
        conn.commit()

    @staticmethod
    def delete_if_empty(year: int, month: int) -> bool:
        """Удалить месяц без аванса, зарплаты, заметки и доп. выплат (остался от доп. выплаты)."""
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            """
            DELETE FROM salaries
            WHERE year = ? AND month = ? AND advance = 0 AND salary = 0 AND note IS NULL
              AND NOT EXISTS (SELECT 1 FROM extra_payments e WHERE e.year = ? AND e.month = ?)
            """,
            (year, month, year, month),
        )
        conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def set_note(year: int, month: int, note: Optional[str]) -> bool:
        """Заменить только заметку месяца; False — записи за месяц нет."""
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            "UPDATE salaries SET note = ? WHERE year = ? AND month = ?",
            (note, year, month),
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
        """
        conn = DatabaseConnection.get_connection()
        try:
            # Вместе с месяцем — его доп. выплаты: иначе они «воскресли» бы
            # при повторном вводе месяца
            conn.execute("DELETE FROM extra_payments WHERE year = ? AND month = ?", (year, month))
            cursor = conn.execute(
                "DELETE FROM salaries WHERE year = ? AND month = ?",
                (year, month)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
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
        try:
            conn.execute("DELETE FROM extra_payments WHERE year = ?", (year,))
            cursor = conn.execute(
                "DELETE FROM salaries WHERE year = ?",
                (year,)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
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
            # created_at пишет SQLite (CURRENT_TIMESTAMP) — это UTC без метки пояса;
            # может быть NULL в старых записях
            created_at=parse_utc(row['created_at']) if row['created_at'] else None,
            note=row['note'] if 'note' in row.keys() else None,
            # Есть только в представлении month_totals (в RETURNING * таблицы — нет)
            extras_total=from_cents(row['extras_total']) if 'extras_total' in row.keys() else 0.0,
        )

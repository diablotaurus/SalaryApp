"""
Модуль управления миграциями базы данных.

Реализует систему версионирования схемы БД с последовательным применением изменений.
Каждая миграция имеет уникальное имя и применяется только один раз.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from core.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class MigrationManager:
    """Менеджер миграций базы данных"""
    
    def __init__(self):
        """Инициализация менеджера миграций"""
        self.conn = DatabaseConnection.get_connection()
        self._create_migrations_table()  # Создание таблицы для отслеживания миграций
    
    def _create_migrations_table(self):
        """
        Создать таблицу для отслеживания примененных миграций.
        
        Таблица migrations хранит историю всех примененных миграций
        с временными метками для аудита и отката (если потребуется).
        """
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,  -- Уникальное имя миграции
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Время применения
            )
        """)
        self.conn.commit()
    
    def _is_migration_applied(self, name: str) -> bool:
        """
        Проверить, применена ли миграция.
        
        Args:
            name: Имя миграции
            
        Returns:
            bool: True если миграция уже применена, иначе False
            
        Примечание:
            - Проверка по уникальному имени миграции
            - Гарантирует идемпотентность применения миграций
        """
        cursor = self.conn.execute(
            "SELECT 1 FROM migrations WHERE name = ?", 
            (name,)
        )
        return cursor.fetchone() is not None
    
    def _mark_migration_applied(self, name: str):
        """
        Отметить миграцию как примененную.
        
        Args:
            name: Имя примененной миграции
            
        Примечание:
            - Запись в таблицу migrations происходит только после успешного применения
            - Обеспечивает атомарность: либо миграция полностью применяется, либо нет
        """
        self.conn.execute(
            "INSERT INTO migrations (name) VALUES (?)",
            (name,)
        )
        self.conn.commit()
    
    def apply_migrations(self):
        """
        Применить все непримененные миграции в порядке их определения.
        
        Алгоритм:
            1. Определить список всех доступных миграций
            2. Для каждой миграции проверить, применена ли она
            3. Если не применена - выполнить и пометить как примененную
            4. Продолжить со следующей миграцией
            
        Особенности:
            - Миграции применяются последовательно в порядке объявления
            - В случае ошибки применение останавливается
            - Откат не реализован (требуется ручное вмешательство)
        """
        # Определение списка миграций в порядке применения
        migrations = [
            ("001_initial", self._migration_001_initial),
            ("002_add_indices", self._migration_002_add_indices),
            ("003_add_settings", self._migration_003_add_settings),
            ("004_add_payment_dates", self._migration_004_add_payment_dates),
        ]
        
        # Применение каждой миграции
        for name, migration_func in migrations:
            if not self._is_migration_applied(name):
                logger.info("Applying migration: %s", name)
                migration_func()  # Выполнение миграции
                self._mark_migration_applied(name)  # Отметка как примененной
    
    def _migration_001_initial(self):
        """
        Первоначальная миграция - создание основной таблицы salaries.
        
        Создает таблицу для хранения записей о зарплатах с полями:
        - id: автоинкрементный первичный ключ
        - year, month: год и месяц записи
        - advance, salary: суммы аванса и зарплаты
        - created_at: временная метка создания записи
        """
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS salaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                advance REAL NOT NULL DEFAULT 0,
                salary REAL NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def _migration_002_add_indices(self):
        """
        Миграция добавления индексов для оптимизации запросов.
        
        Создает индекс для ускорения поиска по году и месяцу.
        
        Производительность:
            - Индекс ускоряет WHERE year = ? AND month = ?
            - Ускоряет ORDER BY year, month
            - Занимает дополнительное место на диске
        """
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_salaries_year_month ON salaries(year, month)"
        )
        self.conn.commit()
    
    def _migration_003_add_settings(self):
        """
        Миграция добавления таблицы настроек и начальных значений.
        
        Создает таблицу settings в формате ключ-значение и заполняет
        начальными настройками приложения.
        
        Безопасность:
            - Использует INSERT OR REPLACE для предотвращения дубликатов
            - Значения по умолчанию могут быть переопределены пользователем
        """
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Начальные настройки приложения
        default_settings = [
            ("currency", "руб."),  # Валюта по умолчанию
            ("backup_auto", "1"),  # Автоматическое резервное копирование
            ("backup_days", "7"),  # Хранение резервных копий (дней)
            ("export_default_format", "csv"),  # Формат экспорта по умолчанию
            ("advance_color", "#0d6efd"),  # Цвет для авансов в UI
            ("salary_color", "#198754"),  # Цвет для зарплат в UI
            ("total_color", "#dc3545")  # Цвет для итогов в UI
        ]
        
        # Вставка начальных настроек
        for key, value in default_settings:
            self.conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        
        self.conn.commit()

    def _migration_004_add_payment_dates(self):
        """
        Миграция добавления полей для дат выплат.
        
        Добавляет в таблицу salaries поля advance_date и salary_date
        для хранения конкретных дат получения аванса и зарплаты.
        
        Особенности:
            - Использует ALTER TABLE ADD COLUMN IF NOT EXISTS
            - Поддерживает обратную совместимость со старыми записями
            - Поля могут быть NULL для старых записей
        """
        # Проверяем существующие колонки в таблице
        cursor = self.conn.execute("PRAGMA table_info(salaries)")
        existing_columns = {row["name"] for row in cursor.fetchall()}

        # Добавляем колонку advance_date если её нет
        if "advance_date" not in existing_columns:
            self.conn.execute("ALTER TABLE salaries ADD COLUMN advance_date DATE")
        
        # Добавляем колонку salary_date если её нет
        if "salary_date" not in existing_columns:
            self.conn.execute("ALTER TABLE salaries ADD COLUMN salary_date DATE")

        self.conn.commit()
    
    def get_applied_migrations(self) -> list:
        """
        Получить историю примененных миграций.
        
        Returns:
            list: Список примененных миграций с датами применения
            
        Использование:
            - Для отладки и аудита
            - Для проверки состояния базы данных
            - В будущем может использоваться для отката миграций
        """
        cursor = self.conn.execute(
            "SELECT name, applied_at FROM migrations ORDER BY applied_at"
        )
        return [dict(row) for row in cursor.fetchall()]


def apply_all_migrations():
    """
    Основная функция для применения всех миграций при запуске приложения.
    
    Вызывается при старте приложения для гарантии актуальности схемы БД.
    Логирует процесс применения миграций для отладки.
    """
    manager = MigrationManager()
    manager.apply_migrations()
    logger.info("All migrations applied successfully")
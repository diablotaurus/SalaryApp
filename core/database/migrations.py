"""
Модуль управления миграциями базы данных.

Реализует систему версионирования схемы БД с последовательным применением изменений.
Каждая миграция имеет уникальное имя и применяется только один раз.
"""

import logging
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
            ("005_salary_integrity", self._migration_005_salary_integrity),
            ("006_month_notes", self._migration_006_month_notes),
            ("007_extra_payments", self._migration_007_extra_payments),
        ]
        
        # Применение каждой миграции
        for name, migration_func in migrations:
            try:
                if self._is_migration_applied(name):
                    continue
                if name == "005_salary_integrity":
                    self._backup_before_salary_integrity_migration()
                self.conn.execute("BEGIN IMMEDIATE")
                logger.info("Applying migration: %s", name)
                migration_func()
                self._mark_migration_applied(name)
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                logger.exception("Migration failed: %s", name)
                raise

    def _backup_before_salary_integrity_migration(self) -> None:
        """Back up non-empty databases before the destructive table rebuild."""
        row_count = self.conn.execute("SELECT COUNT(*) FROM salaries").fetchone()[0]
        if not row_count:
            return

        from core.services.backup_service import BackupService

        backup_path = BackupService.create_backup(
            "Автоматическая копия перед миграцией 005_salary_integrity"
        )
        logger.info("Pre-migration backup created: %s", backup_path)
    
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
            ("backup_days", "30"),  # Хранение резервных копий (дней)
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

    def _migration_005_salary_integrity(self):
        """Store money as integer kopecks and enforce period integrity."""
        invalid_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM salaries
            WHERE year NOT BETWEEN 2000 AND 2100
               OR month NOT BETWEEN 1 AND 12
               OR typeof(advance) NOT IN ('integer', 'real')
               OR typeof(salary) NOT IN ('integer', 'real')
               OR advance < 0
               OR salary < 0
            """
        ).fetchone()[0]
        if invalid_count:
            raise RuntimeError(
                "Миграция остановлена: в salaries найдены некорректные строки "
                f"({invalid_count})."
            )

        duplicate_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT year, month
                FROM salaries
                GROUP BY year, month
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        if duplicate_count:
            raise RuntimeError(
                "Миграция остановлена: найдены повторяющиеся месяцы "
                f"({duplicate_count})."
            )

        self.conn.execute(
            """
            CREATE TABLE salaries_v005 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL CHECK (year BETWEEN 2000 AND 2100),
                month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
                advance INTEGER NOT NULL DEFAULT 0 CHECK (advance >= 0),
                salary INTEGER NOT NULL DEFAULT 0 CHECK (salary >= 0),
                advance_date TEXT,
                salary_date TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (year, month)
            )
            """
        )
        self.conn.execute(
            """
            INSERT INTO salaries_v005 (
                id, year, month, advance, salary,
                advance_date, salary_date, created_at
            )
            SELECT
                id,
                year,
                month,
                CAST(ROUND(advance * 100) AS INTEGER),
                CAST(ROUND(salary * 100) AS INTEGER),
                advance_date,
                salary_date,
                COALESCE(created_at, CURRENT_TIMESTAMP)
            FROM salaries
            """
        )
        self.conn.execute("DROP TABLE salaries")
        self.conn.execute("ALTER TABLE salaries_v005 RENAME TO salaries")
        self.conn.execute(
            """
            CREATE UNIQUE INDEX idx_salaries_year_month
            ON salaries(year, month)
            """
        )
    
    def _migration_006_month_notes(self):
        """
        Заметка к месяцу («отпуск 2 недели», «повышение с 1-го»).

        Только добавление колонки (NULL у существующих записей): данные не
        переписываются, поэтому копия перед миграцией не нужна. Прежние версии
        приложения колонку не читают и не мешают ей (INSERT перечисляет колонки).
        """
        cursor = self.conn.execute("PRAGMA table_info(salaries)")
        if "note" not in {row["name"] for row in cursor.fetchall()}:
            self.conn.execute("ALTER TABLE salaries ADD COLUMN note TEXT")

    def _migration_007_extra_payments(self):
        """
        Доп. выплаты (отпускные, премии, больничные, прочее) и представление
        month_totals — месяц вместе с суммой его доп. выплат.

        Чтения истории и SQL-аналитика идут через month_totals, поэтому итоги
        везде включают доп. выплаты. Существующие данные не меняются; прежние
        версии приложения новую таблицу и представление не используют.
        """
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS extra_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL CHECK (year BETWEEN 2000 AND 2100),
                month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
                kind TEXT NOT NULL CHECK (kind IN ('vacation', 'bonus', 'sick', 'other')),
                amount INTEGER NOT NULL CHECK (amount > 0),
                paid_date TEXT,
                comment TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_extra_payments_year_month ON extra_payments(year, month)"
        )
        self.conn.execute(
            """
            CREATE VIEW IF NOT EXISTS month_totals AS
            SELECT s.*, COALESCE(e.extras, 0) AS extras_total
            FROM salaries AS s
            LEFT JOIN (
                SELECT year, month, SUM(amount) AS extras
                FROM extra_payments
                GROUP BY year, month
            ) AS e ON e.year = s.year AND e.month = s.month
            """
        )


def apply_all_migrations():
    """
    Основная функция для применения всех миграций при запуске приложения.
    
    Вызывается при старте приложения для гарантии актуальности схемы БД.
    Логирует процесс применения миграций для отладки.
    """
    manager = MigrationManager()
    manager.apply_migrations()
    logger.info("All migrations applied successfully")

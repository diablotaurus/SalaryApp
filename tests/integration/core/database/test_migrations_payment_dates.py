import sqlite3
import zipfile

from core.config.settings import config
from core.database.connection import DatabaseConnection
from core.database.migrations import apply_all_migrations


def test_migrations_create_payment_date_columns(temp_db):
    conn = DatabaseConnection.get_connection()
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(salaries)").fetchall()}

    assert "advance_date" in columns
    assert "salary_date" in columns


def test_migrations_are_idempotent_for_payment_date_columns(temp_db):
    apply_all_migrations()

    conn = DatabaseConnection.get_connection()
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(salaries)").fetchall()}

    assert "advance_date" in columns
    assert "salary_date" in columns


def test_salary_integrity_migration_adds_constraints(temp_db):
    conn = DatabaseConnection.get_connection()
    indexes = conn.execute("PRAGMA index_list(salaries)").fetchall()
    index_by_name = {row[1]: row for row in indexes}

    assert index_by_name["idx_salaries_year_month"][2] == 1

    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'salaries'"
    ).fetchone()[0]
    assert "CHECK (month BETWEEN 1 AND 12)" in schema
    assert "CHECK (advance >= 0)" in schema


def test_salary_integrity_migration_backs_up_existing_database(tmp_path):
    old_path = config.db.path
    old_backup_dir = config.db.backup_dir
    database_path = tmp_path / "legacy.db"
    backup_dir = tmp_path / "backup"

    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE salaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            advance REAL NOT NULL DEFAULT 0,
            salary REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            advance_date DATE,
            salary_date DATE
        );
        INSERT INTO salaries (year, month, advance, salary)
        VALUES (2026, 1, 123.45, 678.90);
        INSERT INTO migrations (name) VALUES
            ('001_initial'), ('002_add_indices'),
            ('003_add_settings'), ('004_add_payment_dates');
        """
    )
    connection.close()

    DatabaseConnection.close_connection()
    config.db.path = str(database_path)
    config.db.backup_dir = str(backup_dir)
    try:
        apply_all_migrations()

        backups = list(backup_dir.glob("salary_backup_*.zip"))
        assert len(backups) == 1
        with zipfile.ZipFile(backups[0]) as archive:
            assert "salary.db" in archive.namelist()

        migrated = DatabaseConnection.get_connection()
        row = migrated.execute(
            "SELECT advance, salary, typeof(advance), typeof(salary) FROM salaries"
        ).fetchone()
        assert tuple(row) == (12345, 67890, "integer", "integer")
    finally:
        DatabaseConnection.close_connection()
        config.db.path = old_path
        config.db.backup_dir = old_backup_dir

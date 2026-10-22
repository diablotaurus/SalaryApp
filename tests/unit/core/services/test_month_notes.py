import csv
import sqlite3
from pathlib import Path

import pytest

from core.config.settings import config
from core.database.connection import DatabaseConnection
from core.database.migrations import apply_all_migrations
from core.services.export_service import ExportService
from core.services.salary_service import SalaryService


def test_note_is_saved_kept_replaced_and_cleared(temp_db):
    SalaryService.add_salary(2026, 7, 1.0, 2.0, note="  отпуск   2 недели ")
    assert SalaryService.get_salary(2026, 7).note == "отпуск 2 недели"  # в одну строку

    SalaryService.add_salary(2026, 7, 3.0, 4.0)  # бот: note=None — заметка остаётся
    assert SalaryService.get_salary(2026, 7).note == "отпуск 2 недели"

    SalaryService.add_salary(2026, 7, 3.0, 4.0, note="повышение")
    assert SalaryService.get_salary(2026, 7).note == "повышение"

    SalaryService.add_salary(2026, 7, 3.0, 4.0, note="")  # форма: поле стёрли
    assert SalaryService.get_salary(2026, 7).note is None


def test_note_length_is_limited(temp_db):
    with pytest.raises(ValueError, match="200"):
        SalaryService.add_salary(2026, 7, 1.0, 2.0, note="я" * 201)
    SalaryService.add_salary(2026, 7, 1.0, 2.0, note="я" * 200)


def test_set_note_changes_only_note(temp_db):
    SalaryService.add_salary(2026, 8, 100.0, 200.0, "28.08.2026", "14.09.2026")

    saved = SalaryService.set_note(2026, 8, "премия")

    assert (saved.note, saved.advance, saved.salary) == ("премия", 100.0, 200.0)
    assert saved.salary_date.strftime("%d.%m.%Y") == "14.09.2026"
    assert SalaryService.set_note(2026, 8, "").note is None


def test_set_note_requires_existing_month(temp_db):
    with pytest.raises(ValueError, match="сначала внесите месяц"):
        SalaryService.set_note(2026, 9, "отпуск")


def test_notes_reach_month_grid_and_dict(temp_db):
    SalaryService.add_salary(2026, 3, 1.0, 2.0, note="больничный")

    months = SalaryService.get_year_with_all_months(2026)["months"]

    assert months[2]["note"] == "больничный"
    assert months[3]["note"] == ""
    assert SalaryService.get_salary(2026, 3).to_dict()["note"] == "больничный"


def test_export_has_note_column(temp_db, tmp_path: Path):
    SalaryService.add_salary(2026, 3, 1.0, 2.0, note="больничный")
    old_dir = config.export.export_dir
    config.export.export_dir = str(tmp_path)
    try:
        path = Path(ExportService.export_to_csv())
    finally:
        config.export.export_dir = old_dir

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file, delimiter=";"))
    assert rows[0][-1] == "Заметка"
    assert rows[1][-1] == "больничный"


def test_migration_adds_note_column_to_existing_database(tmp_path):
    # База версии до заметок: колонки note нет, данные должны сохраниться
    database = tmp_path / "old.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
                                 applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO migrations (name) VALUES ('001_initial'), ('002_add_indices'), ('003_add_settings'),
                                             ('004_add_payment_dates'), ('005_salary_integrity');
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE salaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL, month INTEGER NOT NULL,
            advance INTEGER NOT NULL DEFAULT 0, salary INTEGER NOT NULL DEFAULT 0,
            advance_date TEXT, salary_date TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (year, month)
        );
        INSERT INTO salaries (year, month, advance, salary) VALUES (2025, 5, 12345, 67890);
        """
    )
    connection.close()

    old_path = config.db.path
    DatabaseConnection.close_connection()
    config.db.path = str(database)
    try:
        apply_all_migrations()
        record = SalaryService.get_salary(2025, 5)
        assert (record.advance, record.salary, record.note) == (123.45, 678.9, None)
        SalaryService.set_note(2025, 5, "старый месяц")
        assert SalaryService.get_salary(2025, 5).note == "старый месяц"
    finally:
        DatabaseConnection.close_connection()
        config.db.path = old_path

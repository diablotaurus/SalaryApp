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


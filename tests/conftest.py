from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config.settings import config
from core.database.connection import DatabaseConnection
from core.database.migrations import apply_all_migrations


@pytest.fixture
def temp_db(tmp_path: Path):
    old_path = config.db.path
    old_backup_dir = config.db.backup_dir
    test_db_path = tmp_path / "salary_test.db"

    DatabaseConnection.close_connection()
    config.db.path = str(test_db_path)
    config.db.backup_dir = str(tmp_path / "backup")
    apply_all_migrations()

    try:
        yield test_db_path
    finally:
        DatabaseConnection.close_connection()
        config.db.path = old_path
        config.db.backup_dir = old_backup_dir

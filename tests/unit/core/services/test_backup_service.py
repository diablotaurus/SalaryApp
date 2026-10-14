import sqlite3
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from core.config.settings import config
from core.services.backup_service import BackupService
from core.services.salary_service import SalaryService
from core.services.settings_service import SettingsService


def test_create_and_list_backup(temp_db, tmp_path: Path):
    old_backup_dir = config.db.backup_dir
    config.db.backup_dir = str(tmp_path)
    try:
        backup_path = BackupService.create_backup("test backup")
        backup_file = Path(backup_path)

        assert backup_file.exists()
        assert backup_file.suffix == ".zip"

        with zipfile.ZipFile(backup_file, "r") as zf:
            names = set(zf.namelist())
            assert "backup_info.json" in names
            assert any(name.endswith(".db") for name in names)

        backups = BackupService.list_backups()
        assert len(backups) >= 1
        assert backups[0]["filename"].endswith(".zip")
        assert backups[0]["comment"] == "test backup"
        assert "created_at" in backups[0]
    finally:
        config.db.backup_dir = old_backup_dir


def test_get_backup_info_and_delete_backup(temp_db, tmp_path: Path):
    old_backup_dir = config.db.backup_dir
    config.db.backup_dir = str(tmp_path)
    try:
        backup_path = BackupService.create_backup("info check")
        info = BackupService.get_backup_info(backup_path)

        assert info["filename"].endswith(".zip")
        assert "size_mb" in info
        assert "backup_date" in info

        deleted = BackupService.delete_backup(backup_path)
        assert deleted is True
        assert not Path(backup_path).exists()
    finally:
        config.db.backup_dir = old_backup_dir


def test_restore_backup_returns_false_for_missing_file(temp_db):
    assert BackupService.restore_backup("Z:/definitely/missing/backup.zip") is False


def test_restore_backup_replaces_data_through_sqlite_backup_api(temp_db, tmp_path: Path):
    old_backup_dir = config.db.backup_dir
    config.db.backup_dir = str(tmp_path)
    try:
        SalaryService.add_salary(2025, 6, 100.25, 200.75)
        backup_path = BackupService.create_backup("before update")

        SalaryService.add_salary(2025, 6, 900.0, 800.0)
        assert BackupService.restore_backup(backup_path) is True

        restored = SalaryService.get_salary(2025, 6)
        assert restored is not None
        assert restored.advance == 100.25
        assert restored.salary == 200.75
    finally:
        config.db.backup_dir = old_backup_dir


def test_delete_backup_rejects_path_outside_backup_directory(temp_db, tmp_path: Path):
    old_backup_dir = config.db.backup_dir
    config.db.backup_dir = str(tmp_path / "allowed")
    outside_file = tmp_path / "salary_backup_outside.zip"
    outside_file.write_bytes(b"not a backup")
    try:
        assert BackupService.delete_backup(str(outside_file)) is False
        assert outside_file.exists()
    finally:
        config.db.backup_dir = old_backup_dir


def test_restore_rejects_nested_database_member(temp_db, tmp_path: Path):
    old_backup_dir = config.db.backup_dir
    config.db.backup_dir = str(tmp_path)
    archive_path = tmp_path / "salary_backup_unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../unsafe.db", b"not sqlite")
    try:
        assert BackupService.restore_backup(str(archive_path)) is False
        assert not (tmp_path.parent / "unsafe.db").exists()
    finally:
        config.db.backup_dir = old_backup_dir


def _old_backup(backup_dir: Path, days_ago: int) -> Path:
    stamp = (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")
    path = backup_dir / f"salary_backup_{stamp}_120000_000000.zip"
    path.write_bytes(b"old backup")
    return path


@pytest.mark.parametrize(
    ("backup_days", "kept"),
    [
        ("90", True),   # пользователь хранит копии 90 дней — 60-дневная остаётся
        ("30", False),  # 30 дней — 60-дневная удаляется
    ],
)
def test_cleanup_uses_backup_days_setting_for_manual_backup(temp_db, tmp_path: Path, backup_days, kept):
    # Раньше настройка учитывалась только при автокопии на закрытии,
    # а ручные копии чистили всё старше 30 дней.
    old_backup_dir = config.db.backup_dir
    config.db.backup_dir = str(tmp_path)
    try:
        SettingsService.set_settings({"backup_days": backup_days})
        old_file = _old_backup(tmp_path, days_ago=60)
        very_old_file = _old_backup(tmp_path, days_ago=120)

        BackupService.create_backup("manual")

        assert old_file.exists() is kept
        assert not very_old_file.exists()
    finally:
        config.db.backup_dir = old_backup_dir


def test_retention_falls_back_to_config_when_setting_unavailable(monkeypatch):
    def broken_setting(*_args, **_kwargs):
        raise sqlite3.OperationalError("no such table: settings")

    monkeypatch.setattr(
        "core.services.backup_service.SettingsService.get_setting", broken_setting
    )

    assert BackupService._retention_days() == config.db.backup_retention_days

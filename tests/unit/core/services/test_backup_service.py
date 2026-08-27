import zipfile
from pathlib import Path

from core.config.settings import config
from core.services.backup_service import BackupService
from core.services.salary_service import SalaryService


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

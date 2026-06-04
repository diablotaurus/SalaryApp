import zipfile
from pathlib import Path

from core.config.settings import config
from core.services.backup_service import BackupService


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


"""Consistent and path-safe SQLite backup management."""
from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List

from core.config.settings import config
from core.database.connection import DatabaseConnection
from core.database.migrations import apply_all_migrations
from core.exceptions import BackupError, SalaryAppError
from core.services.settings_service import SettingsService
from core.utils.clock import utc_now

logger = logging.getLogger(__name__)

BACKUP_PREFIX = "salary_backup_"
DATABASE_MEMBER = "salary.db"
MAX_DATABASE_SIZE = 2 * 1024 * 1024 * 1024


class BackupService:
    """Create, inspect, restore, and delete SQLite backup archives."""

    @staticmethod
    def _backup_dir() -> Path:
        backup_dir = Path(config.db.backup_dir).resolve()
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    @staticmethod
    def _resolve_backup_path(backup_path: str | Path, *, must_exist: bool) -> Path:
        backup_dir = BackupService._backup_dir()
        candidate = Path(backup_path)
        if not candidate.is_absolute():
            direct_candidate = backup_dir / candidate
            candidate = (
                direct_candidate
                if direct_candidate.exists()
                else candidate.resolve(strict=False)
            )
        candidate = candidate.resolve(strict=False)

        if (
            candidate.parent != backup_dir
            or candidate.suffix.lower() != ".zip"
            or not candidate.name.startswith(BACKUP_PREFIX)
        ):
            raise BackupError(
                f"Недопустимый путь резервной копии: {candidate}",
                user_message="Выбран недопустимый файл резервной копии",
            )
        if must_exist and not candidate.is_file():
            raise FileNotFoundError(candidate)
        return candidate

    @staticmethod
    def _validate_database(database_path: Path) -> None:
        if not database_path.is_file() or database_path.stat().st_size == 0:
            raise BackupError("Backup database is empty")
        if database_path.stat().st_size > MAX_DATABASE_SIZE:
            raise BackupError("Backup database exceeds the allowed size")

        uri = f"{database_path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            result = connection.execute("PRAGMA quick_check").fetchone()
            if not result or result[0] != "ok":
                raise BackupError(f"SQLite quick_check failed: {result}")
            table = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = 'salaries'
                """
            ).fetchone()
            if table is None:
                raise BackupError("Backup database has no salaries table")
        finally:
            connection.close()

    @staticmethod
    def _create_database_snapshot(snapshot_path: Path) -> None:
        source = DatabaseConnection.get_connection()
        destination = sqlite3.connect(str(snapshot_path))
        try:
            source.backup(destination)
        finally:
            destination.close()
        BackupService._validate_database(snapshot_path)

    @staticmethod
    def create_backup(comment: str = "") -> str:
        backup_dir = BackupService._backup_dir()
        # Время копии — UTC; «Z» в конце метки однозначно это обозначает.
        # Старые копии (до перехода на стандарт) названы по местному времени.
        created = utc_now()
        timestamp = created.strftime("%Y%m%d_%H%M%S_%fZ")
        backup_path = backup_dir / f"{BACKUP_PREFIX}{timestamp}.zip"
        temporary_archive = backup_path.with_suffix(".zip.tmp")

        normalized_comment = str(comment or "").strip()[:500]
        try:
            with tempfile.TemporaryDirectory(dir=backup_dir) as temporary_dir:
                snapshot_path = Path(temporary_dir) / DATABASE_MEMBER
                BackupService._create_database_snapshot(snapshot_path)
                metadata = {
                    "backup_date": created.isoformat(),  # ISO 8601, UTC (+00:00)
                    "comment": normalized_comment,
                    "app_version": config.app.version,
                    "database_size": snapshot_path.stat().st_size,
                }

                with zipfile.ZipFile(
                    temporary_archive, "w", zipfile.ZIP_DEFLATED
                ) as archive:
                    archive.write(snapshot_path, DATABASE_MEMBER)
                    archive.writestr(
                        "backup_info.json",
                        json.dumps(metadata, ensure_ascii=False, indent=2),
                    )
            os.replace(temporary_archive, backup_path)
            BackupService._cleanup_old_backups()
            return str(backup_path)
        except Exception as exc:
            temporary_archive.unlink(missing_ok=True)
            if isinstance(exc, BackupError):
                raise
            raise BackupError(
                f"Failed to create backup: {exc}",
                user_message="Не удалось создать резервную копию",
            ) from exc

    @staticmethod
    def _retention_days() -> int:
        """
        Срок хранения копий: настройка пользователя backup_days.

        Применяется ко всем копиям — ручным, из web, при закрытии и перед
        восстановлением. Если настройку прочитать нельзя (например, таблицы
        settings ещё нет), используется значение из конфигурации.
        """
        try:
            return int(SettingsService.get_setting("backup_days"))
        except (SalaryAppError, sqlite3.Error, TypeError, ValueError):
            logger.warning("Не удалось прочитать backup_days, срок хранения по умолчанию")
            return config.db.backup_retention_days

    @staticmethod
    def _cleanup_old_backups() -> None:
        """
        Удалить копии старше срока хранения.

        Возраст считается по дате в имени файла (начало суток, UTC) и
        сравнивается с моментом «сейчас минус срок» в UTC. Имена старых копий —
        в местном времени (МСК): расхождение в 3 часа на сроке хранения в днях
        роли не играет.
        """
        backup_dir = BackupService._backup_dir()
        cutoff = utc_now() - timedelta(days=BackupService._retention_days())
        for backup_file in backup_dir.glob(f"{BACKUP_PREFIX}*.zip"):
            try:
                date_str = backup_file.stem[len(BACKUP_PREFIX) :][:8]
                file_day = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
                if file_day < cutoff:
                    backup_file.unlink()
                    logger.info("Deleted old backup: %s", backup_file)
            except (OSError, ValueError):
                logger.exception("Error processing backup file %s", backup_file)

    @staticmethod
    def _read_metadata(backup_file: Path) -> dict[str, Any]:
        with zipfile.ZipFile(backup_file, "r") as archive:
            if "backup_info.json" not in archive.namelist():
                return {}
            metadata_member = archive.getinfo("backup_info.json")
            if metadata_member.file_size > 64 * 1024:
                raise BackupError("Backup metadata is too large")
            with archive.open(metadata_member) as metadata_file:
                metadata = json.load(metadata_file)
                return metadata if isinstance(metadata, dict) else {}

    @staticmethod
    def list_backups() -> List[Dict[str, Any]]:
        backups: list[dict[str, Any]] = []
        for backup_file in sorted(
            BackupService._backup_dir().glob(f"{BACKUP_PREFIX}*.zip"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        ):
            info = BackupService.get_backup_info(str(backup_file))
            if info:
                backups.append(info)
        return backups

    @staticmethod
    def _extract_database(backup_file: Path, destination: Path) -> None:
        with zipfile.ZipFile(backup_file, "r") as archive:
            database_members = [
                member
                for member in archive.infolist()
                if member.filename.lower().endswith(".db")
            ]
            if len(database_members) != 1:
                raise BackupError("Backup must contain exactly one database file")

            member = database_members[0]
            member_path = PurePosixPath(member.filename)
            if member_path.name != member.filename or member.is_dir():
                raise BackupError("Unsafe database member path in backup")
            if member.file_size <= 0 or member.file_size > MAX_DATABASE_SIZE:
                raise BackupError("Invalid database size in backup")

            with archive.open(member, "r") as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)

    @staticmethod
    def restore_backup(backup_path: str) -> bool:
        try:
            backup_file = BackupService._resolve_backup_path(
                backup_path, must_exist=True
            )
            with tempfile.TemporaryDirectory(
                dir=BackupService._backup_dir()
            ) as temporary_dir:
                restored_database = Path(temporary_dir) / DATABASE_MEMBER
                BackupService._extract_database(backup_file, restored_database)
                BackupService._validate_database(restored_database)

                BackupService.create_backup(
                    "Автоматическая копия перед восстановлением"
                )
                source = sqlite3.connect(str(restored_database))
                target = DatabaseConnection.get_connection()
                try:
                    source.backup(target)
                finally:
                    source.close()

            DatabaseConnection.close_connection()
            apply_all_migrations()
            return True
        except (BackupError, FileNotFoundError, OSError, sqlite3.Error, zipfile.BadZipFile):
            logger.exception("Error restoring backup")
            return False

    @staticmethod
    def delete_backup(backup_path: str) -> bool:
        try:
            backup_file = BackupService._resolve_backup_path(
                backup_path, must_exist=True
            )
            backup_file.unlink()
            return True
        except (BackupError, FileNotFoundError, OSError):
            logger.exception("Error deleting backup")
            return False

    @staticmethod
    def get_backup_info(backup_path: str) -> Dict[str, Any]:
        try:
            backup_file = BackupService._resolve_backup_path(
                backup_path, must_exist=True
            )
            file_info = backup_file.stat()
            # Моменты файловой системы — timezone-aware UTC; в МСК их переводит интерфейс
            created = datetime.fromtimestamp(file_info.st_ctime, timezone.utc)
            modified = datetime.fromtimestamp(file_info.st_mtime, timezone.utc)
            info: dict[str, Any] = {
                "filename": backup_file.name,
                "path": str(backup_file),
                "size": file_info.st_size,
                "size_bytes": file_info.st_size,
                "size_mb": round(file_info.st_size / (1024 * 1024), 2),
                "created": created,
                "modified": modified,
                "created_at": created.isoformat(),
                "modified_at": modified.isoformat(),
            }
            info.update(BackupService._read_metadata(backup_file))
            return info
        except (BackupError, FileNotFoundError, OSError, ValueError, zipfile.BadZipFile):
            logger.exception("Error getting backup info")
            return {}

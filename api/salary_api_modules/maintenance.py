from __future__ import annotations

from core.services.backup_service import BackupService
from core.services.export_service import ExportService
from api.common import execute_with_default_error, failure, success


def _resolve_listed_backup(reference: str) -> str | None:
    """Resolve either a listed filename or its full safe path."""
    for backup in BackupService.list_backups():
        if reference in {backup.get("filename"), backup.get("path")}:
            return str(backup["path"])
    return None


def export_data(format_type: str = "csv") -> dict:
    def _action() -> dict:
        if format_type == "csv":
            filepath = ExportService.export_to_csv()
        elif format_type == "json":
            filepath = ExportService.export_to_json()
        elif format_type == "excel":
            filepath = ExportService.export_to_excel()
        else:
            return failure(
                f'Формат "{format_type}" не поддерживается',
                error="Неизвестный формат",
            )

        return success(
            {"filepath": filepath, "format": format_type},
            message=f"Данные успешно экспортированы в {format_type}",
        )

    return execute_with_default_error(_action, "Ошибка при экспорте данных")


def create_backup(comment: str = "") -> dict:
    def _action() -> dict:
        filepath = BackupService.create_backup(comment)
        return success(
            {"filepath": filepath, "comment": comment},
            message="Резервная копия успешно создана",
        )

    return execute_with_default_error(_action, "Ошибка при создании резервной копии")


def list_backups() -> dict:
    def _action() -> dict:
        backups = BackupService.list_backups()
        return success(backups, count=len(backups))

    return execute_with_default_error(
        _action,
        "Ошибка при получении списка резервных копий",
    )


def restore_backup(reference: str) -> dict:
    def _action() -> dict:
        backup_path = _resolve_listed_backup(reference)
        if not backup_path:
            return failure("Резервная копия не найдена", error="not found")
        if not BackupService.restore_backup(backup_path):
            return failure("Не удалось восстановить резервную копию", error="restore failed")
        return success(message="База данных успешно восстановлена")

    return execute_with_default_error(_action, "Ошибка при восстановлении резервной копии")


def delete_backup(reference: str) -> dict:
    def _action() -> dict:
        backup_path = _resolve_listed_backup(reference)
        if not backup_path:
            return failure("Резервная копия не найдена", error="not found")
        if not BackupService.delete_backup(backup_path):
            return failure("Не удалось удалить резервную копию", error="delete failed")
        return success(message="Резервная копия удалена")

    return execute_with_default_error(_action, "Ошибка при удалении резервной копии")

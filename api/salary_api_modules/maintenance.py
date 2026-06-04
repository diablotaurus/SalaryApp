from __future__ import annotations

from core.services.backup_service import BackupService
from core.services.export_service import ExportService
from api.common import execute_with_default_error, failure, success


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

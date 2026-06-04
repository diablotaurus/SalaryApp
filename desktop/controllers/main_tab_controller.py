from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from api.salary_api import SalaryAPI
from core.config.settings import config
from core.exceptions import RECOVERABLE_EXCEPTIONS, to_app_error
from core.repositories.settings_repository import SettingsRepository
from core.services.backup_service import BackupService
from core.services.salary_service import SalaryService
from core.utils.dates import DateUtils
from desktop.views.dialogs.backup_dialog import BackupDialog
from desktop.views.dialogs.export_dialog import ExportDialog
from desktop.views.dialogs.salary_dialog import SalaryDialog

logger = logging.getLogger(__name__)


class MainTabController:
    def __init__(self, navigation: Any):
        self.navigation = navigation
        self.app = navigation.app

    def add_data(self):
        current_year, current_month = SalaryService.get_current_period()
        dialog = SalaryDialog(self.app, self.navigation, current_year, current_month)
        dialog.grab_set()

    def edit_year(self, year: int):
        dialog = SalaryDialog(self.app, self.navigation, year, 1)
        dialog.grab_set()

    def delete_year(self, year: int) -> bool:
        try:
            confirm = self.navigation.show_message(
                "Удаление года",
                (
                    f"Вы уверены, что хотите удалить все данные за {year} год?\n"
                    "Это действие нельзя отменить."
                ),
                "question",
            )
            if not confirm:
                return False

            response = SalaryAPI.delete_year(year)
            if response["success"]:
                self.navigation.show_message("Успех", response["message"], "info")
                self.navigation.refresh_history()
                self.navigation.refresh_reports()
                return True

            self.navigation.show_message("Ошибка", response["message"], "error")
            return False
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Не удалось удалить данные за год")
            self.navigation.show_message(
                "Ошибка",
                app_exc.user_message,
                "error",
            )
            return False

    def refresh_history(self):
        try:
            response = SalaryAPI.get_all_grouped_by_year()
            if response["success"]:
                self.app.main_view.display_years(response["data"])
                stats_response = SalaryAPI.get_statistics()
                if stats_response["success"]:
                    self.app.main_view.update_statistics(stats_response["data"])
            else:
                self.navigation.show_message("Ошибка", response["message"], "error")
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Не удалось обновить историю")
            self.navigation.show_message("Ошибка", app_exc.user_message, "error")

    def export_history(self):
        dialog = ExportDialog(self.app, self.navigation)
        dialog.grab_set()

    def show_backups(self):
        dialog = BackupDialog(self.app, self.navigation)
        dialog.grab_set()

    def save_salary_data(
        self,
        year: int,
        month: int,
        advance: float,
        salary: float,
        advance_date: Optional[str] = None,
        salary_date: Optional[str] = None,
    ) -> bool:
        try:
            response = SalaryAPI.add_salary(
                year,
                month,
                advance,
                salary,
                advance_date=advance_date,
                salary_date=salary_date,
            )
            if response["success"]:
                self.navigation.refresh_history()
                return True

            self.navigation.show_message("Ошибка", response["message"], "error")
            return False
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Не удалось сохранить данные")
            self.navigation.show_message("Ошибка", app_exc.user_message, "error")
            return False

    def get_salary_data(self, year: int, month: int) -> Optional[Dict[str, Any]]:
        try:
            response = SalaryAPI.get_salary(year, month)
            return response["data"] if response["success"] else None
        except RECOVERABLE_EXCEPTIONS:
            return None

    def delete_salary_data(self, year: int, month: int) -> Dict[str, Any]:
        try:
            response = SalaryAPI.delete_salary(year, month)
            if response["success"]:
                self.navigation.refresh_history()
            return response
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Не удалось удалить данные за выбранный период")
            return {"success": False, "message": app_exc.user_message, "error": str(app_exc)}

    @staticmethod
    def get_next_month(year: int, month: int) -> tuple[int, int]:
        return DateUtils.get_next_month(year, month)

    def perform_export(self, format_type: str) -> bool:
        try:
            response = SalaryAPI.export_data(format_type)
            if response["success"]:
                filepath = response["data"]["filepath"]
                message = f"Данные успешно экспортированы в файл:\n{filepath}"
                self.navigation.show_message("Успех", message, "info")
                return True

            self.navigation.show_message("Ошибка", response["message"], "error")
            return False
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Не удалось выполнить экспорт")
            self.navigation.show_message("Ошибка", app_exc.user_message, "error")
            return False

    def create_backup(self, comment: str = "") -> bool:
        try:
            response = SalaryAPI.create_backup(comment)
            if response["success"]:
                self.navigation.show_message("Успех", "Резервная копия успешно создана", "info")
                return True

            self.navigation.show_message("Ошибка", response["message"], "error")
            return False
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Не удалось создать резервную копию")
            self.navigation.show_message(
                "Ошибка",
                app_exc.user_message,
                "error",
            )
            return False

    def get_backups_list(self) -> List[Dict[str, Any]]:
        try:
            response = SalaryAPI.list_backups()
            return response["data"] if response["success"] else []
        except RECOVERABLE_EXCEPTIONS:
            return []

    def restore_backup(self, backup_path: str) -> bool:
        try:
            if BackupService.restore_backup(backup_path):
                self.navigation.show_message("Успех", "База данных успешно восстановлена", "info")
                self.navigation.refresh_history()
                self.navigation.refresh_reports()
                return True

            self.navigation.show_message("Ошибка", "Не удалось восстановить базу данных", "error")
            return False
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Ошибка при восстановлении")
            self.navigation.show_message("Ошибка", app_exc.user_message, "error")
            return False

    def delete_backup(self, backup_path: str) -> bool:
        try:
            if BackupService.delete_backup(backup_path):
                self.navigation.show_message("Успех", "Резервная копия удалена", "info")
                return True

            self.navigation.show_message("Ошибка", "Не удалось удалить резервную копию", "error")
            return False
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Ошибка при удалении")
            self.navigation.show_message("Ошибка", app_exc.user_message, "error")
            return False

    def create_auto_backup_on_close(self) -> bool:
        """
        Создать автоматическую резервную копию при закрытии приложения.

        Returns:
            bool: True, если резервная копия создана; False, если автокопирование выключено
                  или в процессе возникла ошибка.
        """
        try:
            raw_auto = SettingsRepository.get_setting("backup_auto", "1")
            is_enabled = str(raw_auto).strip().lower() in ("1", "true", "yes", "y", "on")
            if not is_enabled:
                return False

            raw_days = SettingsRepository.get_setting("backup_days", str(config.db.backup_retention_days))
            try:
                retention_days = max(1, int(str(raw_days).strip()))
            except (TypeError, ValueError):
                retention_days = config.db.backup_retention_days

            previous_retention = config.db.backup_retention_days
            config.db.backup_retention_days = retention_days
            try:
                BackupService.create_backup("auto_on_close")
            finally:
                config.db.backup_retention_days = previous_retention
            return True
        except Exception:
            logger.exception("Auto backup on close failed")
            return False

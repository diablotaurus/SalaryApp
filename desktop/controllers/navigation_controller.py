"""
Navigation controller orchestrating tab-specific controllers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from desktop.controllers.main_tab_controller import MainTabController
from desktop.controllers.report_tab_controller import ReportTabController
from desktop.controllers.settings_tab_controller import SettingsTabController


class NavigationController:
    """Facade controller that keeps public API stable for desktop UI."""

    def __init__(self, app):
        self.app = app
        self.current_year = None
        self.current_month = None

        self._main_tab = MainTabController(self)
        self._report_tab = ReportTabController(self)
        self._settings_tab = SettingsTabController(self)

    def show_main_view(self):
        self.app.notebook.select(0)
        self.refresh_history()

    def show_message(self, title: str, message: str, message_type: str = "info"):
        return self.app.show_message(title, message, message_type)

    def add_data(self):
        self._main_tab.add_data()

    def edit_year(self, year: int):
        self._main_tab.edit_year(year)

    def delete_year(self, year: int):
        return self._main_tab.delete_year(year)

    def refresh_history(self):
        self._main_tab.refresh_history()

    def export_history(self):
        self._main_tab.export_history()

    def show_backups(self):
        self._main_tab.show_backups()

    def refresh_reports(self):
        self._report_tab.refresh_reports()

    def on_year_selected(self, year: int):
        self._report_tab.on_year_selected(year)

    def refresh_settings(self):
        self._settings_tab.refresh_settings()

    def save_settings(self, settings: Dict[str, Any]):
        return self._settings_tab.save_settings(settings)

    def save_salary_data(
        self,
        year: int,
        month: int,
        advance: float,
        salary: float,
        advance_date: Optional[str] = None,
        salary_date: Optional[str] = None,
    ) -> bool:
        return self._main_tab.save_salary_data(
            year,
            month,
            advance,
            salary,
            advance_date=advance_date,
            salary_date=salary_date,
        )

    def get_salary_data(self, year: int, month: int) -> Optional[Dict[str, Any]]:
        return self._main_tab.get_salary_data(year, month)

    def delete_salary_data(self, year: int, month: int) -> Dict[str, Any]:
        return self._main_tab.delete_salary_data(year, month)

    def get_next_month(self, year: int, month: int) -> tuple[int, int]:
        return self._main_tab.get_next_month(year, month)

    def perform_export(self, format_type: str) -> bool:
        return self._main_tab.perform_export(format_type)

    def create_backup(self, comment: str = "") -> bool:
        return self._main_tab.create_backup(comment)

    def get_backups_list(self) -> List[Dict[str, Any]]:
        return self._main_tab.get_backups_list()

    def restore_backup(self, backup_path: str) -> bool:
        return self._main_tab.restore_backup(backup_path)

    def delete_backup(self, backup_path: str) -> bool:
        return self._main_tab.delete_backup(backup_path)

    def create_auto_backup_on_close(self) -> bool:
        return self._main_tab.create_auto_backup_on_close()

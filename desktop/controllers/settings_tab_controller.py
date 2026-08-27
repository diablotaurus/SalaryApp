from __future__ import annotations

from typing import Any, Dict

from api.settings_api import SettingsAPI
from core.exceptions import RECOVERABLE_EXCEPTIONS, to_app_error


class SettingsTabController:
    def __init__(self, navigation: Any):
        self.navigation = navigation
        self.app = navigation.app

    def refresh_settings(self):
        try:
            response = SettingsAPI.get_settings()
            if response["success"]:
                self.app.settings_view.update_settings(response["data"])
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Не удалось загрузить настройки")
            self.navigation.show_message("Ошибка", app_exc.user_message, "error")

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        try:
            response = SettingsAPI.set_settings(settings)
            if not response["success"]:
                self.navigation.show_message("Ошибка", response["message"], "error")
                return False
            self.navigation.refresh_history()
            self.navigation.show_message("Успех", "Настройки успешно сохранены", "info")
            return True
        except RECOVERABLE_EXCEPTIONS as exc:
            app_exc = to_app_error(exc, "Не удалось сохранить настройки")
            self.navigation.show_message("Ошибка", app_exc.user_message, "error")
            return False

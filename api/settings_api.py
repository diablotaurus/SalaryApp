"""
API-слой для работы с настройками приложения.

Предоставляет CRUD-операции для управления настройками в формате ключ-значение.
Настройки хранятся в БД (таблица settings) и доступны во всех компонентах приложения.

Обработка ошибок и форма ответа унифицированы с остальным API
(см. api/salary_api_modules/common.py).
"""

from typing import Any, Dict

from api.common import execute_with_default_error, failure, success
from core.repositories.settings_repository import SettingsRepository


class SettingsAPI:
    """API класс для управления настройками приложения"""

    @staticmethod
    def get_settings() -> Dict[str, Any]:
        """
        Получить все настройки приложения.

        Returns:
            Dict: Словарь всех настроек (ключ-значение) с количеством записей
        """
        def _action() -> dict:
            settings = SettingsRepository.get_all_settings()
            return success(settings, count=len(settings))

        return execute_with_default_error(_action, "Ошибка при получении настроек")

    @staticmethod
    def get_setting(key: str, default: Any = None) -> Dict[str, Any]:
        """
        Получить конкретную настройку по ключу.

        Args:
            key: Ключ настройки (строка)
            default: Значение по умолчанию, если настройка не найдена

        Returns:
            Dict: Настройка с ключом и значением

        Безопасность:
            - Ключ передаётся как параметр SQL-запроса (защита от инъекций)
        """
        def _action() -> dict:
            value = SettingsRepository.get_setting(key, default)
            return success({"key": key, "value": value})

        return execute_with_default_error(_action, f"Ошибка при получении настройки {key}")

    @staticmethod
    def set_setting(key: str, value: Any) -> Dict[str, Any]:
        """
        Установить или обновить настройку.

        Args:
            key: Ключ настройки
            value: Значение настройки (будет преобразовано в строку)

        Returns:
            Dict: Результат операции сохранения

        Примечание:
            - Значение преобразуется в строку для хранения в БД
            - При сохранении обновляется timestamp (updated_at)
        """
        def _action() -> dict:
            SettingsRepository.set_setting(key, value)
            return success(
                {"key": key, "value": value},
                message=f"Настройка {key} успешно сохранена",
            )

        return execute_with_default_error(_action, f"Ошибка при сохранении настройки {key}")

    @staticmethod
    def delete_setting(key: str) -> Dict[str, Any]:
        """
        Удалить настройку по ключу.

        Args:
            key: Ключ удаляемой настройки

        Returns:
            Dict: Результат операции удаления

        Внимание:
            - После удаления пользовательской настройки используется значение по умолчанию
        """
        def _action() -> dict:
            if SettingsRepository.delete_setting(key):
                return success(message=f"Настройка {key} успешно удалена")
            # Настройка не найдена - это не ошибка, а нормальная ситуация
            return failure(f"Настройка {key} не найдена", error="Настройка не найдена")

        return execute_with_default_error(_action, f"Ошибка при удалении настройки {key}")

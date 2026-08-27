from typing import Any, Dict, Mapping
from core.database.connection import DatabaseConnection


class SettingsRepository:
    """Репозиторий для работы с настройками"""
    
    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        """Получить значение настройки"""
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            "SELECT value FROM settings WHERE key = ?", 
            (key,)
        )
        row = cursor.fetchone()
        return row['value'] if row else default
    
    @staticmethod
    def set_setting(key: str, value: Any) -> None:
        """Установить значение настройки"""
        SettingsRepository.set_settings({key: value})

    @staticmethod
    def set_settings(settings: Mapping[str, Any]) -> None:
        """Атомарно сохранить несколько настроек."""
        conn = DatabaseConnection.get_connection()
        try:
            conn.executemany(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                [(key, str(value)) for key, value in settings.items()],
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    @staticmethod
    def get_all_settings() -> Dict[str, str]:
        """Получить все настройки"""
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute("SELECT key, value FROM settings")
        return {row['key']: row['value'] for row in cursor.fetchall()}
    
    @staticmethod
    def delete_setting(key: str) -> bool:
        """Удалить настройку"""
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0

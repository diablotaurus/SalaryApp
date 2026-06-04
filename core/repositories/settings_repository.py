from typing import Optional, Dict, Any
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
    def set_setting(key: str, value: Any):
        """Установить значение настройки"""
        conn = DatabaseConnection.get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        conn.commit()
    
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
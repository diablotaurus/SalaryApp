"""
Модуль подключения к базе данных.

Реализует потокобезопасное подключение к SQLite с использованием thread-local хранилища.
Обеспечивает создание таблиц при инициализации.
"""

import sqlite3
import threading
import logging
from pathlib import Path
from typing import Optional

from core.config.settings import config

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Потокобезопасное подключение к SQLite (thread-local singleton)"""
    
    # Thread-local хранилище для подключений
    _local = threading.local()
    
    @staticmethod
    def get_connection() -> sqlite3.Connection:
        """
        Получить подключение к БД (thread-local).
        
        Возвращает уникальное подключение для каждого потока.
        Это обеспечивает потокобезопасность при работе с SQLite.
        
        Returns:
            sqlite3.Connection: Подключение к базе данных
            
        Примечание:
            Подключение автоматически создается при первом вызове в каждом потоке.
        """
        if not hasattr(DatabaseConnection._local, 'connection'):
            db_path = Path(config.db.path)
            
            # Логируем подключение для отладки
            logger.info("[DATABASE] Подключаемся к: %s", db_path)
            if config.app.is_production:
                logger.warning("[DATABASE] ВНИМАНИЕ: Работа с реальной базой данных!")
            
            # Создаем директорию для БД, если её нет
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Создаем подключение с настройками:
            # - check_same_thread=False: позволяет использовать подключение в разных потоках
            # - timeout=10: время ожидания блокировки базы (секунды)
            conn = sqlite3.connect(
                str(db_path),
                check_same_thread=False,
                timeout=10
            )
            # Устанавливаем row_factory для возврата строк в виде словарей
            conn.row_factory = sqlite3.Row
            DatabaseConnection._local.connection = conn
            
            # Включаем поддержку внешних ключей (PRAGMA foreign_keys)
            conn.execute("PRAGMA foreign_keys = ON")
            
        return DatabaseConnection._local.connection
    
    @staticmethod
    def close_connection():
        """Закрыть подключение текущего потока"""
        if hasattr(DatabaseConnection._local, 'connection'):
            DatabaseConnection._local.connection.close()
            delattr(DatabaseConnection._local, 'connection')

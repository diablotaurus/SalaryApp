"""
Общий модуль логирования старта desktop-приложения.

Модуль предоставляет функции для настройки логирования при запуске приложения.
Основная особенность - поддержка конфигурирования через settings.py с fallback на значения по умолчанию.
"""
from __future__ import annotations

import logging
import platform
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_startup_logging(base_dir: Path) -> None:
    """
    Основная функция настройки логирования при старте приложения.
    
    Args:
        base_dir: Базовый каталог для разрешения относительных путей к лог-файлам
        
    Примечание:
        Если корневой логгер уже имеет обработчики, функция завершается без изменений.
        Это предотвращает повторную настройку логирования при многократных вызовах.
    """
    root = logging.getLogger()
    if root.handlers:
        return  # Логирование уже настроено, выходим

    # Определение пути к лог-файлу с учетом конфигурации
    log_path = _resolve_startup_log_path(base_dir)
    # Создание директории для логов, если она не существует
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Создание ротируемого файлового обработчика
    # Максимальный размер файла: 5 МБ, сохраняется 3 backup-файла
    handler = RotatingFileHandler(
        filename=str(log_path),
        maxBytes=5 * 1024 * 1024,  # 5 MiB
        backupCount=3,
        encoding="utf-8",
    )
    # Установка форматера для лог-сообщений (время — по МСК с подписью)
    handler.setFormatter(_create_formatter(_resolve_log_format()))

    # Настройка корневого логгера
    root.setLevel(_resolve_log_level())
    root.handlers.clear()  # Очистка существующих обработчиков (на всякий случай)
    root.addHandler(handler)

    # Логирование информации о стартовом контексте
    log_startup_context()


def _create_formatter(log_format: str) -> logging.Formatter:
    """
    Форматер со временем по МСК; при сбое импорта — стандартный.

    Как и остальные функции модуля, не даёт ошибке настройки логов
    помешать запуску приложения.
    """
    try:
        from core.utils.logging_setup import MoscowLogFormatter

        return MoscowLogFormatter(log_format)
    except Exception:
        return logging.Formatter(log_format)


def _resolve_startup_log_path(base_dir: Path) -> Path:
    """
    Определение пути к файлу логирования старта приложения.
    
    Args:
        base_dir: Базовый каталог для относительных путей
        
    Returns:
        Path: Полный путь к файлу лога
        
    Примечание:
        Пытается получить путь из конфигурации (config.logging.startup_log_file).
        Если конфигурация недоступна или путь не указан, возвращает путь по умолчанию.
        Поддерживает как абсолютные, так и относительные пути в конфигурации.
    """
    try:
        from core.config.settings import config

        # Безопасное получение пути из конфигурации
        configured = getattr(getattr(config, "logging", None), "startup_log_file", None)
        if configured:
            configured_path = Path(configured)
            if configured_path.is_absolute():
                return configured_path  # Абсолютный путь из конфигурации
            return base_dir / configured_path  # Относительный путь относительно base_dir
    except Exception:
        # В случае любой ошибки при чтении конфигурации используем путь по умолчанию
        pass

    # Путь по умолчанию: logs/startup.log в базовой директории
    return base_dir / "logs" / "startup.log"


def _resolve_log_level() -> int:
    """
    Определение уровня логирования.
    
    Returns:
        int: Уровень логирования (константа из модуля logging)
        
    Примечание:
        Пытается получить уровень из конфигурации (config.logging.level).
        Поддерживаются строковые названия уровней ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
        В случае ошибки возвращает уровень INFO.
    """
    try:
        from core.config.settings import config

        level_name = getattr(getattr(config, "logging", None), "level", None)
        if level_name:
            # Преобразование строки в константу logging
            return getattr(logging, str(level_name).upper(), logging.INFO)
    except Exception:
        # В случае ошибки используем уровень по умолчанию
        pass

    return logging.INFO  # Уровень по умолчанию


def _resolve_log_format() -> str:
    """
    Определение формата лог-сообщений.
    
    Returns:
        str: Строка формата для форматирования лог-сообщений
        
    Примечание:
        Пытается получить формат из конфигурации (config.logging.format).
        В случае ошибки возвращает формат по умолчанию.
    """
    try:
        from core.config.settings import config

        configured = getattr(getattr(config, "logging", None), "format", None)
        if configured:
            return str(configured)
    except Exception:
        # В случае ошибки используем формат по умолчанию
        pass

    # Формат по умолчанию: время, уровень, сообщение
    return "%(asctime)s %(levelname)s %(message)s"


def log_startup_context() -> None:
    """
    Логирование контекстной информации о запуске приложения.
    
    Записывает в лог:
    1. Версию приложения (из конфигурации)
    2. Версию Python
    3. Информацию о платформе
    
    Примечание:
        В случае ошибок при получении информации, используется значение "unknown".
        Это гарантирует, что приложение сможет запуститься даже с поврежденной конфигурацией.
    """
    app_version = "unknown"
    try:
        from core.config.settings import config

        # Получение отображаемого имени приложения с версией
        app_version = getattr(config.app, "display_name_with_version", "unknown")
    except Exception:
        # Если не удалось получить версию приложения, оставляем "unknown"
        pass

    # Логирование информации о контексте запуска
    logging.info("Startup context: app=%s", app_version)
    logging.info("Startup context: python=%s", sys.version.replace("\n", " "))
    logging.info("Startup context: platform=%s", platform.platform())
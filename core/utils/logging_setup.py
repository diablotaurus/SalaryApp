"""
Настройка логирования фоновых процессов (Telegram-бот, web-сервер).

В production они запускаются через pythonw без консоли: всё, что пишется
только в консоль, теряется. Поэтому логи пишутся в файл с ротацией, а копия
в консоль добавляется, лишь когда консоль действительно есть.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from core.config.settings import config

MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MiB на файл
LOG_BACKUP_COUNT = 3


def configure_file_logging(log_file: str, *, console: bool = False) -> None:
    """
    Направить корневой логгер в файл с ротацией.

    Args:
        log_file: Путь к файлу лога
        console: Дополнительно выводить лог в консоль (если она есть)
    """
    formatter = logging.Formatter(str(config.logging.format))

    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, str(config.logging.level).upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(file_handler)

    # У pythonw нет консоли: sys.stderr там равен None
    if console and sys.stderr is not None:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

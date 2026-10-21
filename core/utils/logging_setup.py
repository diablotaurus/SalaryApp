"""
Настройка логирования фоновых процессов (Telegram-бот, web-сервер).

В production они запускаются через pythonw без консоли: всё, что пишется
только в консоль, теряется. Поэтому логи пишутся в файл с ротацией, а копия
в консоль добавляется, лишь когда консоль действительно есть.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from core.config.settings import config
from core.utils.clock import MOSCOW_TZ, MSK_LABEL

MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MiB на файл
LOG_BACKUP_COUNT = 3


class MoscowLogFormatter(logging.Formatter):
    """
    Время записей лога — по МСК с подписью, независимо от часового пояса Windows.

    Текстовые логи читает человек, поэтому по стандарту времени в них МСК:
    «2026-10-15 00:38:43,331 МСК INFO ...».
    """

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        moment = datetime.fromtimestamp(record.created, MOSCOW_TZ)
        if datefmt:
            text = moment.strftime(datefmt)
        else:
            text = f"{moment:%Y-%m-%d %H:%M:%S},{int(record.msecs):03d}"
        return f"{text} {MSK_LABEL}"


def configure_file_logging(log_file: str, *, console: bool = False) -> None:
    """
    Направить корневой логгер в файл с ротацией.

    Args:
        log_file: Путь к файлу лога
        console: Дополнительно выводить лог в консоль (если она есть)
    """
    formatter = MoscowLogFormatter(str(config.logging.format))

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

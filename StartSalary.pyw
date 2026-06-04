"""
Точка входа для desktop-приложения.
Модуль запускает noconsole desktop-приложение и пишет ошибки старта в logs/startup.log.

Примечание: Этот файл предназначен для запуска без консольного окна (расширение .pyw).
Используется для production-запуска приложения.
"""
from __future__ import annotations

import logging
from pathlib import Path

from desktop.main import main
from desktop.startup_logging import setup_startup_logging


if __name__ == "__main__":
    # Настройка логирования старта приложения
    # Путь определяется относительно расположения текущего файла
    setup_startup_logging(Path(__file__).resolve().parent)
    try:
        # Запуск основной функции приложения из модуля desktop.main
        main()
    except Exception:
        # Логирование критической ошибки старта приложения
        # Исключение пробрасывается дальше для завершения работы
        logging.exception("Startup failed")
        raise
"""
Точка входа для desktop приложения.

Модуль выполняет начальную инициализацию приложения, применяет миграции базы данных
и обрабатывает критические ошибки запуска с показом сообщений пользователю.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import tkinter as tk
from tkinter import messagebox

from core.database.migrations import apply_all_migrations
from desktop.app import App
from desktop.startup_logging import setup_startup_logging


def _show_startup_error(title: str, message: str) -> None:
    """
    Показать диалоговое окно с ошибкой запуска.
    
    Args:
        title: Заголовок окна ошибки
        message: Текст сообщения об ошибке
        
    Примечание:
        Создает временное окно Tk() для отображения сообщения,
        даже если основное приложение не может запуститься.
    """
    try:
        # Создаем временное окно для отображения ошибки
        root = tk.Tk()
        root.withdraw()  # Скрываем основное окно
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        # Если даже диалог ошибки не может показаться, логируем в консоль
        logging.exception("Failed to show startup error dialog")
        print(f"{title}\n{message}", file=sys.stderr)


def main() -> None:
    """Основная функция запуска приложения"""
    # Настройка логирования старта (путь определяется относительно desktop/main.py)
    setup_startup_logging(Path(__file__).resolve().parent.parent)

    try:
        # Применяем миграции базы данных перед запуском приложения
        apply_all_migrations()
    except Exception as e:
        logging.exception("Database migrations failed")
        _show_startup_error(
            "Ошибка запуска приложения",
            f"Не удалось применить миграции базы данных:\n\n{e}",
        )
        return

    try:
        # Создаем и запускаем основное приложение
        app = App()
        app.run()
    except Exception as e:
        logging.exception("Application startup failed")
        _show_startup_error(
            "Ошибка запуска приложения",
            f"Не удалось запустить приложение:\n\n{e}",
        )


if __name__ == "__main__":
    # Проверка, что модуль запускается как пакет
    if __package__ in (None, ""):
        # Если запускается напрямую, а не как модуль - показываем ошибку
        setup_startup_logging(Path(__file__).resolve().parent.parent)
        logging.error("Desktop main should be started as a package: python -m desktop")
        _show_startup_error(
            "Ошибка запуска приложения",
            "Запускайте приложение через StartSalary.pyw или как пакет: python -m desktop",
        )
        sys.exit(1)

    main()
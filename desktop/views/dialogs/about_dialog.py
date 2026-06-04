"""
Модальное окно «О программе».

Открывается кнопкой на вкладке «Настройки». Показывает название приложения,
версию, краткое описание, автора, лицензию и кликабельную ссылку на репозиторий.
"""

import tkinter as tk
import webbrowser
from tkinter import ttk

from core.config.settings import config
from desktop.widgets.dialogs import BaseDialog
from desktop.views.constants import (
    BUTTON_DIALOG_WIDTH,
    TEXT_CLOSE,
    ABOUT_FRAME_TITLE,
    ABOUT_DESCRIPTION,
    ABOUT_VERSION_LABEL,
    ABOUT_AUTHOR_LABEL,
    ABOUT_AUTHOR,
    ABOUT_LICENSE_LABEL,
    ABOUT_LICENSE,
    ABOUT_GITHUB_LABEL,
    ABOUT_GITHUB_URL,
)


class AboutDialog(BaseDialog):
    """Модальное окно «О программе»."""

    def __init__(self, parent):
        super().__init__(parent, ABOUT_FRAME_TITLE)
        self.resizable(False, False)
        self._create_widgets()
        # Пере-центрируем после построения содержимого (теперь размер известен).
        self._center_on_parent()

    def _create_widgets(self):
        """Создать виджеты окна."""
        main = ttk.Frame(self, padding=24)
        main.pack(fill=tk.BOTH, expand=True)

        # Название приложения и версия
        ttk.Label(
            main,
            text=config.app.display_name,
            font=("Segoe UI", 14, "bold"),
            anchor=tk.CENTER,
        ).pack(fill=tk.X, pady=(0, 4))
        ttk.Label(
            main,
            text=f"{ABOUT_VERSION_LABEL} {config.app.version}",
            font=("Segoe UI", 11),
            anchor=tk.CENTER,
        ).pack(fill=tk.X, pady=(0, 12))

        # Краткое описание
        ttk.Label(
            main,
            text=ABOUT_DESCRIPTION,
            justify=tk.CENTER,
            wraplength=420,
            anchor=tk.CENTER,
        ).pack(fill=tk.X, pady=(0, 14))

        ttk.Separator(main, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))

        # Автор, лицензия
        info = ttk.Frame(main)
        info.pack()
        self._info_row(info, 0, ABOUT_AUTHOR_LABEL, ABOUT_AUTHOR)
        self._info_row(info, 1, ABOUT_LICENSE_LABEL, ABOUT_LICENSE)

        # Кликабельная ссылка на репозиторий
        link_row = ttk.Frame(main)
        link_row.pack(pady=(12, 0))
        ttk.Label(link_row, text=ABOUT_GITHUB_LABEL, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        link = ttk.Label(link_row, text=ABOUT_GITHUB_URL, foreground="#0d6efd", cursor="hand2")
        link.pack(side=tk.LEFT, padx=(6, 0))
        link.bind("<Button-1>", lambda _event: self._open_url(ABOUT_GITHUB_URL))

        # Кнопка закрытия
        ttk.Button(main, text=TEXT_CLOSE, command=self.destroy,
                   width=BUTTON_DIALOG_WIDTH).pack(pady=(20, 0))

        # Закрытие по Escape
        self.bind("<Escape>", lambda _event: self.destroy())

    @staticmethod
    def _info_row(parent, row: int, label: str, value: str):
        """Строка «метка: значение», выровненная вокруг центра."""
        ttk.Label(parent, text=label, font=("Segoe UI", 9, "bold")).grid(
            row=row, column=0, sticky=tk.E, padx=(0, 6), pady=2
        )
        ttk.Label(parent, text=value).grid(row=row, column=1, sticky=tk.W, pady=2)

    @staticmethod
    def _open_url(url: str):
        """Открыть ссылку в браузере по умолчанию."""
        try:
            webbrowser.open(url)
        except Exception:
            # Если браузер недоступен — молча игнорируем (не критично).
            pass

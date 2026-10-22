"""
Всплывающая подсказка над виджетом: появляется при наведении, исчезает при уходе.

Используется для заметки к месяцу в карточке на «Главной».
"""
from __future__ import annotations

import tkinter as tk
from typing import Optional

BACKGROUND = "#ffffe0"
DELAY_MS = 350
WRAP_PX = 320
OFFSET_PX = 14


class Tooltip:
    """Подсказка с текстом; привязки добавляются к существующим (add="+")."""

    def __init__(self, widget: tk.Misc, text: str):
        self.widget = widget
        self.text = text
        self._window: Optional[tk.Toplevel] = None
        self._pending: Optional[str] = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._pending = self.widget.after(DELAY_MS, self._show)

    def _cancel(self) -> None:
        if self._pending is not None:
            self.widget.after_cancel(self._pending)
            self._pending = None

    def _show(self) -> None:
        self._pending = None
        if self._window is not None:
            return
        x = self.widget.winfo_pointerx() + OFFSET_PX
        y = self.widget.winfo_pointery() + OFFSET_PX
        self._window = window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            window, text=self.text, background=BACKGROUND, relief="solid", borderwidth=1,
            justify="left", wraplength=WRAP_PX, padx=6, pady=3, font=("Segoe UI", 9),
        ).pack()

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._window is not None:
            self._window.destroy()
            self._window = None

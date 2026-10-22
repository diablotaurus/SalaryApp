"""Окно добавления доп. выплаты (отпускные, премия, больничные, прочее) к месяцу."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from core.models.extra_payment import EXTRA_KINDS
from core.utils.dates import DateUtils
from core.utils.money import MoneyUtils
from desktop.views.constants import (
    BUTTON_DIALOG_WIDTH, DIALOG_TITLE_ERROR, ENTRY_WIDTH, PADX_DEFAULT, PADY_DEFAULT,
)
from desktop.widgets.dialogs import BaseDialog

KIND_BY_NAME = {name: kind for kind, name in EXTRA_KINDS.items()}


class ExtraPaymentDialog(BaseDialog):
    """Вид, сумма, дата получения и комментарий; сохраняется сразу по «Добавить»."""

    def __init__(self, parent, controller, year: int, month: int, on_saved: Callable[[], None]):
        period = f"{DateUtils.get_month_name(month).lower()} {year}"
        super().__init__(parent, f"Доп. выплата — {DateUtils.get_month_name(month)} {year}")
        self.controller = controller
        self.year, self.month = year, month
        self.on_saved = on_saved
        self.resizable(False, False)

        self.kind_var = tk.StringVar(value=EXTRA_KINDS["bonus"])
        self.amount_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.comment_var = tk.StringVar()
        self._create_widgets(period)
        self._center_on_main_window()
        self.amount_entry.focus_set()

    def _create_widgets(self, period: str) -> None:
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=f"Доп. выплата за {period}", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 12)
        )

        rows = [
            ("Вид:", ttk.Combobox(frame, textvariable=self.kind_var, values=list(EXTRA_KINDS.values()),
                                   state="readonly", width=ENTRY_WIDTH - 2)),
            ("Сумма:", ttk.Entry(frame, textvariable=self.amount_var, width=ENTRY_WIDTH)),
            ("Дата получения:", ttk.Entry(frame, textvariable=self.date_var, width=ENTRY_WIDTH)),
            ("Комментарий:", ttk.Entry(frame, textvariable=self.comment_var, width=ENTRY_WIDTH * 2)),
        ]
        for index, (label, widget) in enumerate(rows, start=1):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky=tk.W, padx=(0, PADX_DEFAULT), pady=(0, PADY_DEFAULT))
            widget.grid(row=index, column=1, sticky=tk.W, pady=(0, PADY_DEFAULT))
        self.amount_entry = rows[1][1]
        ttk.Label(
            frame, text="Дата — ДД.ММ.ГГГГ, можно оставить пустой", font=("Segoe UI", 8), foreground="#666666"
        ).grid(row=len(rows) + 1, column=1, sticky=tk.W, pady=(0, 12))

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(rows) + 2, column=0, columnspan=2)
        ttk.Button(buttons, text="Добавить", command=self._save, style="Success.TButton",
                   width=BUTTON_DIALOG_WIDTH).pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
        ttk.Button(buttons, text="Отмена", command=self.destroy, width=BUTTON_DIALOG_WIDTH).pack(side=tk.LEFT)
        self.bind("<Return>", lambda _e: self._save())
        self.bind("<Escape>", lambda _e: self.destroy())

    def _save(self) -> None:
        try:
            amount = MoneyUtils.parse_amount(self.amount_var.get(), "сумма")
        except ValueError as exc:
            messagebox.showerror(DIALOG_TITLE_ERROR, str(exc), parent=self)
            return
        saved = self.controller.add_extra_payment(
            self.year,
            self.month,
            KIND_BY_NAME[self.kind_var.get()],
            amount,
            self.date_var.get().strip() or None,
            self.comment_var.get().strip() or None,
        )
        if saved:
            self.destroy()
            self.on_saved()

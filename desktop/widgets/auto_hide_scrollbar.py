"""
Полоса прокрутки, которая показывается только когда есть что прокручивать.
"""
from tkinter import ttk


class AutoHideScrollbar(ttk.Scrollbar):
    """
    ttk.Scrollbar, скрывающаяся, когда содержимое помещается целиком.

    Размещать нужно через grid: grid_remove() прячет полосу, запоминая
    параметры размещения, и повторный grid() возвращает её на то же место.
    Освободившееся место занимает соседний виджет (например, Canvas).
    """

    def set(self, first, last):
        """Вызывается прокручиваемым виджетом (yscrollcommand) при каждом изменении вида."""
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
        super().set(first, last)

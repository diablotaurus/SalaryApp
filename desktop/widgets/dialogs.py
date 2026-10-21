import tkinter as tk
from typing import Optional

from desktop.widgets.window_centering import center_on_main_window


class BaseDialog(tk.Toplevel):
    """Базовый класс для всех диалоговых окон"""
    
    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent)
        
        # Настройка окна
        self.title(title)
        
        # Сохраняем ссылку на родительское окно
        self.parent = parent
        
        # Делаем окно модальным
        self.transient(parent)
        self.grab_set()

        # Центрирует окно наследник — после построения содержимого, когда известен
        # его размер (_center_on_main_window). Предварительное центрирование здесь
        # (с размером пустого окна) не нужно: при двух позициях до показа окна
        # Tk иногда применял первую, и окно оказывалось не по центру.

    def _center_on_main_window(self, width: Optional[int] = None, height: Optional[int] = None):
        """
        Центрировать окно по главному окну приложения (а не по непосредственному родителю).

        Args:
            width, height: Размер окна, если он задаётся явно
        """
        center_on_main_window(self, width, height)


import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable

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


class ConfirmationDialog(BaseDialog):
    """Диалог подтверждения"""
    
    def __init__(self, parent, title: str, message: str):
        # Вызываем конструктор базового класса
        super().__init__(parent, title)
        
        self.result = None
        
        # Настройка окна
        self._center_on_main_window(400, 150)
        self.resizable(False, False)
        
        # Создаем интерфейс
        self._create_widgets(title, message)
    
    def _create_widgets(self, title: str, message: str):
        """Создать виджеты"""
        # Основной контейнер
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        title_label = ttk.Label(main_frame, text=title, font=('Segoe UI', 11, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Сообщение
        message_label = ttk.Label(main_frame, text=message, wraplength=350)
        message_label.pack(pady=(0, 20))
        
        # Панель кнопок
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Кнопка Да
        yes_button = ttk.Button(
            button_frame,
            text="Да",
            command=lambda: self._set_result(True),
            style="Success.TButton"
        )
        yes_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Кнопка Нет
        no_button = ttk.Button(
            button_frame,
            text="Нет",
            command=lambda: self._set_result(False)
        )
        no_button.pack(side=tk.LEFT)
    
    def _set_result(self, result: bool):
        """Установить результат"""
        self.result = result
        self.destroy()
    
    def show(self) -> Optional[bool]:
        """Показать диалог и вернуть результат"""
        self.wait_window()
        return self.result


class InputDialog(BaseDialog):
    """Диалог ввода"""
    
    def __init__(self, parent, title: str, prompt: str, default: str = ""):
        # Вызываем конструктор базового класса
        super().__init__(parent, title)
        
        self.result = None
        
        # Настройка окна
        self._center_on_main_window(400, 150)
        self.resizable(False, False)
        
        # Создаем интерфейс
        self._create_widgets(title, prompt, default)
        
        # Фокус на поле ввода
        self.entry.focus_set()
    
    def _create_widgets(self, title: str, prompt: str, default: str):
        """Создать виджеты"""
        # Основной контейнер
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Подсказка
        prompt_label = ttk.Label(main_frame, text=prompt)
        prompt_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Поле ввода
        self.entry_var = tk.StringVar(value=default)
        self.entry = ttk.Entry(main_frame, textvariable=self.entry_var, width=40)
        self.entry.pack(fill=tk.X, pady=(0, 20))
        
        # Панель кнопок
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Кнопка OK
        ok_button = ttk.Button(
            button_frame,
            text="OK",
            command=lambda: self._set_result(self.entry_var.get()),
            style="Success.TButton"
        )
        ok_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Кнопка Отмена
        cancel_button = ttk.Button(
            button_frame,
            text="Отмена",
            command=lambda: self._set_result(None)
        )
        cancel_button.pack(side=tk.LEFT)
        
        # Привязываем клавиши
        self.entry.bind('<Return>', lambda e: self._set_result(self.entry_var.get()))
        self.bind('<Escape>', lambda e: self._set_result(None))
    
    def _set_result(self, result):
        """Установить результат"""
        self.result = result
        self.destroy()
    
    def show(self) -> Optional[str]:
        """Показать диалог и вернуть результат"""
        self.wait_window()
        return self.result


class ProgressDialog(BaseDialog):
    """Диалог прогресса"""
    
    def __init__(self, parent, title: str, message: str):
        # Вызываем конструктор базового класса
        super().__init__(parent, title)
        
        # Настройка окна
        self._center_on_main_window(400, 120)
        self.resizable(False, False)
        
        # Запрещаем закрытие
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Создаем интерфейс
        self._create_widgets(title, message)
    
    def _create_widgets(self, title: str, message: str):
        """Создать виджеты"""
        # Основной контейнер
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Сообщение
        message_label = ttk.Label(main_frame, text=message)
        message_label.pack(pady=(0, 20))
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=300
        )
        self.progress.pack()
        
        # Запускаем анимацию
        self.progress.start(10)
    
    def close(self):
        """Закрыть диалог"""
        self.progress.stop()
        self.destroy()

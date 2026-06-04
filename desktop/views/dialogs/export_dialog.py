import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List
from desktop.widgets.dialogs import BaseDialog
from desktop.views.constants import (
    DIALOG_EXPORT_TITLE, TEXT_EXPORT_TO_FILE, TEXT_SELECT_EXPORT_FORMAT,
    TEXT_CSV_FORMAT, TEXT_JSON_FORMAT, TEXT_EXCEL_FORMAT,
    TEXT_EXPORT_INFO, TEXT_EXPORT_DETAILS,
    TEXT_EXPORT_BUTTON, TEXT_CANCEL_BUTTON,
    TEXT_WRAPLENGTH_EXPORT_INFO, PADX_DEFAULT, PADY_DEFAULT,
    WINDOW_EXPORT_DIALOG_SIZE
)


class ExportDialog(BaseDialog):
    """Диалоговое окно для экспорта данных"""
    
    def __init__(self, parent, controller):
        # Вызываем конструктор базового класса
        super().__init__(parent, DIALOG_EXPORT_TITLE)
        
        self.controller = controller
        self.parent = parent
        
        # Настройка окна
        self.geometry(WINDOW_EXPORT_DIALOG_SIZE)
        self.resizable(False, False)
        self._center_on_parent()
        
        # Создаем интерфейс
        self._create_widgets()
        
        # Фокус на первом поле
        self.format_combobox.focus_set()
    
    def _create_widgets(self):
        """Создать виджеты"""
        # Основной контейнер
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        title_label = ttk.Label(
            main_frame,
            text=TEXT_EXPORT_TO_FILE,
            font=('Segoe UI', 12, 'bold')
        )
        title_label.pack(pady=(0, 15))
        
        # Формат экспорта
        format_frame = ttk.LabelFrame(main_frame, text=TEXT_SELECT_EXPORT_FORMAT, padding=10)
        format_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.format_var = tk.StringVar(value="csv")
        
        # Список форматов
        formats = [
            (TEXT_CSV_FORMAT, "csv"),
            (TEXT_JSON_FORMAT, "json"),
            (TEXT_EXCEL_FORMAT, "excel")
        ]
        
        for text, value in formats:
            rb = ttk.Radiobutton(
                format_frame,
                text=text,
                variable=self.format_var,
                value=value
            )
            rb.pack(anchor=tk.W, pady=2)
        
        # Информация - УВЕЛИЧЕННАЯ КАРТОЧКА
        info_frame = ttk.LabelFrame(main_frame, text=TEXT_EXPORT_INFO, padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Увеличиваем высоту Label
        info_label = ttk.Label(
            info_frame, 
            text=TEXT_EXPORT_DETAILS, 
            justify=tk.LEFT,
            wraplength=TEXT_WRAPLENGTH_EXPORT_INFO,
            font=('Segoe UI', 9)
        )
        info_label.pack(fill=tk.X, expand=True)
        
        # Панель кнопок
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Кнопка Экспортировать
        export_button = ttk.Button(
            button_frame,
            text=TEXT_EXPORT_BUTTON,
            command=self._export_data,
            style="Primary.TButton"
        )
        export_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Кнопка Отмена
        cancel_button = ttk.Button(
            button_frame,
            text=TEXT_CANCEL_BUTTON,
            command=self.destroy
        )
        cancel_button.pack(side=tk.LEFT)
        
        # Привязываем клавиши
        self.bind('<Return>', lambda e: self._export_data())
        self.bind('<Escape>', lambda e: self.destroy())
    
    def _export_data(self):
        """Выполнить экспорт данных"""
        format_type = self.format_var.get()
        
        if format_type:
            if self.controller.perform_export(format_type):
                self.destroy()

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional
from core.utils.dates import DateUtils
from core.utils.money import MoneyUtils
from desktop.widgets.dialogs import BaseDialog
from desktop.views.constants import (
    DIALOG_SALARY_TITLE, TEXT_SELECT_YEAR, TEXT_SELECT_MONTH,
    TEXT_ADVANCE, TEXT_SALARY, TEXT_RUBLES,
    TEXT_ADVANCE_DATE, TEXT_SALARY_DATE, TEXT_DATE_HINT,
    TEXT_SAVE, TEXT_CLEAR, TEXT_CLOSE,
    DIALOG_TITLE_ERROR, ERROR_NO_YEAR_MONTH, ERROR_NEGATIVE_AMOUNTS,
    ERROR_INVALID_FORMAT, ERROR_SAVE_FAILED,
    SUCCESS_TITLE, SUCCESS_SAVE_DATA, SUCCESS_CLEAR_DATA,
    CONFIRM_TITLE, CONFIRM_CLEAR_MONTH_DATA,
    PADX_DEFAULT, PADY_DEFAULT, ENTRY_WIDTH, COMBOBOX_WIDTH, BUTTON_DIALOG_WIDTH
)


class SalaryDialog(BaseDialog):
    """Диалоговое окно для ввода данных по зарплате"""
    
    def __init__(self, parent, controller, year=None, month=None):
        # Вызываем конструктор базового класса
        super().__init__(parent, DIALOG_SALARY_TITLE)
        
        self.controller = controller
        self.parent = parent

        # Настройка окна (размер подгоняется под содержимое автоматически)
        self.resizable(False, False)

        # Инициализация переменных
        self._init_variables(year, month)

        # Создаем интерфейс
        self._create_widgets()

        # Загружаем существующие данные
        self._load_existing_data()

        # Центрируем после построения содержимого (размер уже известен)
        self._center_on_parent()

        # Фокус на первом поле
        self.year_combobox.focus_set()
    
    def _init_variables(self, year, month):
        """Инициализировать переменные"""
        # Получаем текущую дату если не указана
        if year is None or month is None:
            current_year, current_month = DateUtils.get_current_period()
            year = year or current_year
            month = month or current_month
        
        self.year_var = tk.IntVar(value=year)
        self.month_name_var = tk.StringVar(value=DateUtils.get_month_name(month))
        self.advance_var = tk.StringVar(value="0.00")
        self.salary_var = tk.StringVar(value="0.00")
        self.advance_date_var = tk.StringVar(value="")
        self.salary_date_var = tk.StringVar(value="")
        
        # Список лет (от 2020 до текущего + 1)
        current_year = datetime.now().year
        self.years_list = list(range(2020, current_year + 2))
        
        # Список месяцев
        self.months_list = DateUtils.get_months_list()
        
        # Сохраняем номер месяца для внутреннего использования
        self.current_month_number = month
        self.clear_pending = False
    
    def _create_widgets(self):
        """Создать виджеты"""
        # Основной контейнер
        main_frame = ttk.Frame(self, padding=24)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок-шапка
        ttk.Label(
            main_frame,
            text=DIALOG_SALARY_TITLE,
            font=('Segoe UI', 12, 'bold')
        ).pack(pady=(0, 15))

        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=(0, PADY_DEFAULT))

        form_frame.columnconfigure(0, weight=0)
        form_frame.columnconfigure(1, weight=0)
        form_frame.columnconfigure(2, weight=0)

        label_width = 20
        row = 0

        # Поле года
        ttk.Label(form_frame, text=TEXT_SELECT_YEAR, width=label_width, anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=(0, PADX_DEFAULT), pady=(0, PADY_DEFAULT)
        )
        self.year_combobox = ttk.Combobox(
            form_frame,
            textvariable=self.year_var,
            values=self.years_list,
            state="readonly",
            width=COMBOBOX_WIDTH
        )
        self.year_combobox.grid(row=row, column=1, sticky=tk.W, pady=(0, PADY_DEFAULT))
        self.year_combobox.bind("<<ComboboxSelected>>", self._on_year_month_changed)

        # Поле месяца
        row += 1
        ttk.Label(form_frame, text=TEXT_SELECT_MONTH, width=label_width, anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=(0, PADX_DEFAULT), pady=(0, PADY_DEFAULT)
        )
        month_values = [name for _, name in self.months_list]
        self.month_combobox = ttk.Combobox(
            form_frame,
            textvariable=self.month_name_var,
            values=month_values,
            state="readonly",
            width=COMBOBOX_WIDTH
        )
        self.month_combobox.grid(row=row, column=1, sticky=tk.W, pady=(0, PADY_DEFAULT))
        self.month_combobox.bind("<<ComboboxSelected>>", self._on_year_month_changed)

        # Поле аванса
        row += 1
        ttk.Label(form_frame, text=TEXT_ADVANCE, width=label_width, anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=(0, PADX_DEFAULT), pady=(0, PADY_DEFAULT)
        )
        self.advance_entry = ttk.Entry(
            form_frame,
            textvariable=self.advance_var,
            width=ENTRY_WIDTH
        )
        self.advance_entry.grid(row=row, column=1, sticky=tk.W, pady=(0, PADY_DEFAULT), padx=(0, 2))
        ttk.Label(form_frame, text=TEXT_RUBLES).grid(
            row=row, column=2, sticky=tk.W, padx=(0, 0), pady=(0, PADY_DEFAULT)
        )

        # Поле даты аванса
        row += 1
        ttk.Label(form_frame, text=TEXT_ADVANCE_DATE, width=label_width, anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=(0, PADX_DEFAULT), pady=(0, PADY_DEFAULT)
        )
        self.advance_date_entry = ttk.Entry(
            form_frame,
            textvariable=self.advance_date_var,
            width=ENTRY_WIDTH
        )
        self.advance_date_entry.grid(row=row, column=1, sticky=tk.W, pady=(0, PADY_DEFAULT))

        # Поле зарплаты
        row += 1
        ttk.Label(form_frame, text=TEXT_SALARY, width=label_width, anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=(0, PADX_DEFAULT), pady=(0, PADY_DEFAULT)
        )
        self.salary_entry = ttk.Entry(
            form_frame,
            textvariable=self.salary_var,
            width=ENTRY_WIDTH
        )
        self.salary_entry.grid(row=row, column=1, sticky=tk.W, pady=(0, PADY_DEFAULT), padx=(0, 2))
        ttk.Label(form_frame, text=TEXT_RUBLES).grid(
            row=row, column=2, sticky=tk.W, padx=(0, 0), pady=(0, PADY_DEFAULT)
        )

        # Поле даты зарплаты
        row += 1
        ttk.Label(form_frame, text=TEXT_SALARY_DATE, width=label_width, anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=(0, PADX_DEFAULT), pady=(0, 10)
        )
        self.salary_date_entry = ttk.Entry(
            form_frame,
            textvariable=self.salary_date_var,
            width=ENTRY_WIDTH
        )
        self.salary_date_entry.grid(row=row, column=1, sticky=tk.W, pady=(0, 10))

        # Подсказка по формату дат
        ttk.Label(
            main_frame,
            text=TEXT_DATE_HINT,
            font=('Segoe UI', 8),
            foreground="#666666"
        ).pack(anchor=tk.W, pady=(0, PADY_DEFAULT))

        # Панель кнопок
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        buttons_container = ttk.Frame(button_frame)
        buttons_container.pack(anchor=tk.CENTER)

        # Кнопка Сохранить
        save_button = ttk.Button(
            buttons_container,
            text=TEXT_SAVE,
            command=self._save_data,
            style="Success.TButton",
            width=BUTTON_DIALOG_WIDTH
        )
        save_button.pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))

        # Кнопка Очистить
        clear_button = ttk.Button(
            buttons_container,
            text=TEXT_CLEAR,
            command=self._clear_fields,
            width=BUTTON_DIALOG_WIDTH
        )
        clear_button.pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))

        # Кнопка Закрыть
        close_button = ttk.Button(
            buttons_container,
            text=TEXT_CLOSE,
            command=self.destroy,
            width=BUTTON_DIALOG_WIDTH
        )
        close_button.pack(side=tk.LEFT)
        
        # Привязываем клавиши
        self.bind('<Return>', lambda e: self._save_data())
        self.bind('<Escape>', lambda e: self.destroy())
    
    def _on_year_month_changed(self, event=None):
        """Обработчик изменения года или месяца"""
        # Обновляем номер месяца на основе выбранного названия
        month_name = self.month_name_var.get()
        self.current_month_number = DateUtils.get_month_number(month_name)
        self.clear_pending = False
        self._load_existing_data()
    
    def _load_existing_data(self):
        """Загрузить существующие данные"""
        year = self.year_var.get()
        month = self.current_month_number
        
        if year and month:
            # Получаем данные через контроллер
            data = self.controller.get_salary_data(year, month)
            
            if data:
                # Устанавливаем значения из базы данных
                self.advance_var.set(
                    MoneyUtils.format_amount(data.get('advance', 0), '')
                )
                self.salary_var.set(
                    MoneyUtils.format_amount(data.get('salary', 0), '')
                )
                self.advance_date_var.set(data.get('advance_date') or "")
                self.salary_date_var.set(data.get('salary_date') or "")
            else:
                # Очищаем поля если данных нет
                self.advance_var.set("0.00")
                self.salary_var.set("0.00")
                self.advance_date_var.set("")
                self.salary_date_var.set("")
            self.clear_pending = False
    
    def _save_data(self):
        """Сохранить данные"""
        try:
            # Получаем значения
            year = self.year_var.get()
            month = self.current_month_number
            advance = MoneyUtils.parse_amount(self.advance_var.get())
            salary = MoneyUtils.parse_amount(self.salary_var.get())
            advance_date = self.advance_date_var.get().strip()
            salary_date = self.salary_date_var.get().strip()
            
            # Валидация
            if not year or not month:
                messagebox.showerror(DIALOG_TITLE_ERROR, ERROR_NO_YEAR_MONTH)
                return
            
            if advance < 0 or salary < 0:
                messagebox.showerror(DIALOG_TITLE_ERROR, ERROR_NEGATIVE_AMOUNTS)
                return

            should_delete = (
                self.clear_pending and
                advance == 0 and
                salary == 0 and
                not advance_date and
                not salary_date
            )

            if should_delete:
                month_name = DateUtils.get_month_name(month)
                is_confirmed = messagebox.askyesno(
                    CONFIRM_TITLE,
                    CONFIRM_CLEAR_MONTH_DATA.format(month_name=month_name, year=year),
                )
                if not is_confirmed:
                    return

                response = self.controller.delete_salary_data(year, month)
                if response.get("success"):
                    messagebox.showinfo(
                        SUCCESS_TITLE,
                        SUCCESS_CLEAR_DATA.format(message=response.get("message", "")),
                    )
                    self.clear_pending = False
                    self.destroy()
                else:
                    messagebox.showerror(
                        DIALOG_TITLE_ERROR,
                        response.get("message", "Не удалось очистить данные"),
                    )
                return

            self.clear_pending = False
            
            # Сохраняем через контроллер
            if self.controller.save_salary_data(year, month, advance, salary, advance_date, salary_date):
                # Спрашиваем, продолжить ли ввод
                if messagebox.askyesno(
                    SUCCESS_TITLE,
                    SUCCESS_SAVE_DATA
                ):
                    # Переходим к следующему месяцу
                    next_year, next_month = self.controller.get_next_month(year, month)
                    self.year_var.set(next_year)
                    self.month_name_var.set(DateUtils.get_month_name(next_month))
                    self.current_month_number = next_month
                    
                    # Очищаем поля и загружаем данные за следующий месяц
                    self.advance_var.set("0.00")
                    self.salary_var.set("0.00")
                    self.advance_date_var.set("")
                    self.salary_date_var.set("")
                    self._load_existing_data()
                    
                    # Фокус на поле аванса
                    self.advance_entry.focus_set()
                else:
                    self.destroy()
        
        except ValueError as e:
            messagebox.showerror(DIALOG_TITLE_ERROR, ERROR_INVALID_FORMAT.format(error=str(e)))
        except Exception as e:
            messagebox.showerror(DIALOG_TITLE_ERROR, ERROR_SAVE_FAILED.format(error=str(e)))
    
    def _clear_fields(self):
        """Очистить поля ввода"""
        self.clear_pending = True

        # Очищаем суммы и даты без изменения выбранного периода
        self.advance_var.set("0.00")
        self.salary_var.set("0.00")
        self.advance_date_var.set("")
        self.salary_date_var.set("")

        # Фокус на поле аванса
        self.advance_entry.focus_set()

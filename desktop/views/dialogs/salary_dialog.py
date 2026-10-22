import tkinter as tk
from tkinter import ttk, messagebox
from core.utils.dates import DateUtils
from core.utils.money import MoneyUtils
from desktop.views.dialogs.extra_payment_dialog import ExtraPaymentDialog
from desktop.widgets.dialogs import BaseDialog
from desktop.views.constants import (
    DIALOG_SALARY_TITLE, TEXT_SELECT_YEAR, TEXT_SELECT_MONTH,
    TEXT_ADVANCE, TEXT_SALARY, TEXT_RUBLES,
    TEXT_ADVANCE_DATE, TEXT_SALARY_DATE, TEXT_DATE_HINT, TEXT_NOTE, TEXT_NOTE_HINT,
    TEXT_SAVE, TEXT_CLEAR, TEXT_CLOSE,
    DIALOG_TITLE_ERROR, ERROR_NO_YEAR_MONTH, ERROR_NEGATIVE_AMOUNTS,
    ERROR_INVALID_FORMAT, ERROR_SAVE_FAILED,
    SUCCESS_TITLE, SUCCESS_SAVE_DATA, SUCCESS_CLEAR_DATA,
    CONFIRM_TITLE, CONFIRM_CLEAR_MONTH_DATA,
    PADX_DEFAULT, PADY_DEFAULT, ENTRY_WIDTH, COMBOBOX_WIDTH, BUTTON_DIALOG_WIDTH
)


# Пустая сумма в поле ввода — в той же записи, что и сохранённые суммы
ZERO_AMOUNT_TEXT = MoneyUtils.format_amount_plain(0)


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
        self._center_on_main_window()

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
        self.advance_var = tk.StringVar(value=ZERO_AMOUNT_TEXT)
        self.salary_var = tk.StringVar(value=ZERO_AMOUNT_TEXT)
        self.advance_date_var = tk.StringVar(value="")
        self.salary_date_var = tk.StringVar(value="")
        self.note_var = tk.StringVar(value="")
        
        # Список лет (от 2020 до текущего по МСК + 1)
        current_year, _ = DateUtils.get_current_period()
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

        # Заметка к месяцу (необязательно) — своя сетка: широкое поле не должно
        # раздвигать колонку «руб.» у сумм
        note_frame = ttk.Frame(main_frame)
        note_frame.pack(fill=tk.X)
        ttk.Label(note_frame, text=TEXT_NOTE, width=label_width, anchor=tk.W).grid(
            row=0, column=0, sticky=tk.W, padx=(0, PADX_DEFAULT), pady=(0, 2)
        )
        self.note_entry = ttk.Entry(note_frame, textvariable=self.note_var, width=ENTRY_WIDTH * 2)
        self.note_entry.grid(row=0, column=1, sticky=tk.W, pady=(0, 2))
        ttk.Label(
            note_frame, text=TEXT_NOTE_HINT, font=('Segoe UI', 8), foreground="#666666"
        ).grid(row=1, column=1, sticky=tk.W, pady=(0, 10))

        self._create_extras_section(main_frame)

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
    
    def _create_extras_section(self, parent) -> None:
        """Доп. выплаты месяца (отпускные, премии…): список, «Добавить», «Удалить»."""
        frame = ttk.LabelFrame(parent, text="Доп. выплаты месяца (сохраняются сразу)", padding=8)
        frame.pack(fill=tk.X, pady=(0, PADY_DEFAULT))
        columns = ("kind", "amount", "date", "comment")
        self.extras_tree = ttk.Treeview(frame, columns=columns, show="headings", height=3, selectmode="browse")
        for column, title, width, anchor in (
            ("kind", "Вид", 100, tk.W), ("amount", "Сумма", 100, tk.E),
            ("date", "Дата", 90, tk.CENTER), ("comment", "Комментарий", 190, tk.W),
        ):
            self.extras_tree.heading(column, text=title)
            self.extras_tree.column(column, width=width, anchor=anchor, stretch=column == "comment")
        self.extras_tree.pack(fill=tk.X)
        self.extras_tree.bind("<<TreeviewSelect>>", self._on_extra_selected)

        buttons = ttk.Frame(frame)
        buttons.pack(anchor=tk.W, pady=(6, 0))
        ttk.Button(buttons, text="Добавить…", command=self._add_extra).pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
        self.delete_extra_button = ttk.Button(buttons, text="Удалить", command=self._delete_extra, state=tk.DISABLED)
        self.delete_extra_button.pack(side=tk.LEFT)

    def _load_extras(self) -> None:
        self.extras_tree.delete(*self.extras_tree.get_children())
        year, month = self.year_var.get(), self.current_month_number
        for payment in self.controller.get_extra_payments(year, month) if year and month else []:
            self.extras_tree.insert("", tk.END, iid=str(payment["id"]), values=(
                payment["kind_name"],
                MoneyUtils.format_amount_plain(payment["amount"]),
                payment.get("paid_date") or "-",
                payment.get("comment") or "",
            ))
        self.delete_extra_button.config(state=tk.DISABLED)

    def _on_extra_selected(self, _event=None) -> None:
        self.delete_extra_button.config(state=tk.NORMAL if self.extras_tree.selection() else tk.DISABLED)

    def _add_extra(self) -> None:
        ExtraPaymentDialog(self, self.controller, self.year_var.get(), self.current_month_number, self._load_extras)

    def _delete_extra(self) -> None:
        selection = self.extras_tree.selection()
        if not selection:
            return
        kind, amount = self.extras_tree.item(selection[0], "values")[:2]
        if messagebox.askyesno(CONFIRM_TITLE, f"Удалить доп. выплату «{kind}» на {amount}?", parent=self):
            if self.controller.delete_extra_payment(int(selection[0])):
                self._load_extras()

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
                self.note_var.set(data.get('note') or "")
            else:
                # Очищаем поля если данных нет
                self.advance_var.set(ZERO_AMOUNT_TEXT)
                self.salary_var.set(ZERO_AMOUNT_TEXT)
                self.advance_date_var.set("")
                self.salary_date_var.set("")
                self.note_var.set("")
            self.clear_pending = False
            self._load_extras()
    
    def _save_data(self):
        """Сохранить данные"""
        try:
            # Получаем значения
            year = self.year_var.get()
            month = self.current_month_number
            advance = MoneyUtils.parse_amount(self.advance_var.get(), "аванс")
            salary = MoneyUtils.parse_amount(self.salary_var.get(), "зарплата")
            advance_date = self.advance_date_var.get().strip()
            salary_date = self.salary_date_var.get().strip()
            # Поле подставлено из базы: пустое — заметку стёрли
            note = self.note_var.get().strip()
            
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
            if self.controller.save_salary_data(year, month, advance, salary, advance_date, salary_date, note):
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
                    self.advance_var.set(ZERO_AMOUNT_TEXT)
                    self.salary_var.set(ZERO_AMOUNT_TEXT)
                    self.advance_date_var.set("")
                    self.salary_date_var.set("")
                    self.note_var.set("")
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
        self.advance_var.set(ZERO_AMOUNT_TEXT)
        self.salary_var.set(ZERO_AMOUNT_TEXT)
        self.advance_date_var.set("")
        self.salary_date_var.set("")
        self.note_var.set("")

        # Фокус на поле аванса
        self.advance_entry.focus_set()

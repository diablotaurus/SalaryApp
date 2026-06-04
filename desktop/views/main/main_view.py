"""
Главное представление (View) приложения.

Отображает историю заработной платы в виде карточек по годам
с помесячной детализацией. Реализует паттерн View в архитектуре MVC.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any
from desktop.views.base_view import BaseView
from desktop.views.constants import (
    PADX_DEFAULT, PADY_DEFAULT,
    TEXT_ACTIONS, TEXT_ADD_DATA, TEXT_REFRESH_HISTORY, TEXT_EXPORT_HISTORY, TEXT_BACKUP,
    TEXT_EDIT, TEXT_DELETE_YEAR, TEXT_HISTORY_TITLE,
    WINDOW_MAIN_MIN_WIDTH, WINDOW_MAIN_MIN_HEIGHT,
    WINDOW_MAIN_DEFAULT_WIDTH, WINDOW_MAIN_DEFAULT_HEIGHT,
    DEFAULT_HISTORY_LAYOUT_MODE, DEFAULT_MAIN_STATS_LAYOUT_MODE,
    DEFAULT_MONTH_TITLE_FONT_SIZE, DEFAULT_MONTH_TOTAL_FONT_SIZE, DEFAULT_MONTH_DATA_FONT_SIZE
)
from core.utils.money import MoneyUtils
from core.utils.dates import DateUtils
from core.repositories.settings_repository import SettingsRepository
from desktop.views.constants import DEFAULT_ADVANCE_COLOR, DEFAULT_SALARY_COLOR, DEFAULT_TOTAL_COLOR


class MainView(BaseView):
    """Класс главной вкладки с отображением истории зарплат по годам"""
    
    def _create_widgets(self):
        """Создание всех виджетов главной вкладки"""
        # Основной контейнер с отступами
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=PADX_DEFAULT, pady=PADY_DEFAULT)
        
        # Панель кнопок управления
        self._create_button_panel(main_container)
        
        # Панель истории с карточками годов (занимает всё оставшееся пространство)
        self._create_years_panel(main_container)
    
    def _create_button_panel(self, parent):
        """Создать панель с кнопками действий"""
        button_frame = ttk.LabelFrame(parent, text=TEXT_ACTIONS, padding=PADX_DEFAULT)
        button_frame.pack(fill=tk.X, pady=(0, PADY_DEFAULT))
        
        # Контейнер для равномерного размещения кнопок
        button_container = ttk.Frame(button_frame)
        button_container.pack(fill=tk.X)
        
        # Кнопка "Добавить данные"
        self.add_button = ttk.Button(
            button_container,
            text=TEXT_ADD_DATA,
            command=self.controller.add_data,
            style="Primary.TButton"
        )
        self.add_button.pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
        
        # Кнопка "Обновить историю"
        self.refresh_button = ttk.Button(
            button_container,
            text=TEXT_REFRESH_HISTORY,
            command=self.controller.refresh_history
        )
        self.refresh_button.pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
        
        # Кнопка "Экспорт истории"
        self.export_button = ttk.Button(
            button_container,
            text=TEXT_EXPORT_HISTORY,
            command=self.controller.export_history
        )
        self.export_button.pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
        
        # Кнопка "Резервные копии"
        self.backup_button = ttk.Button(
            button_container,
            text=TEXT_BACKUP,
            command=self.controller.show_backups
        )
        self.backup_button.pack(side=tk.LEFT)
    
    def _create_years_panel(self, parent):
        """
        Создать панель истории с карточками годов и поддержкой прокрутки.
        
        Использует Canvas + Scrollbar для реализации скроллинга при большом количестве лет.
        Это обеспечивает хорошую производительность даже с десятками лет данных.
        """
        history_frame = ttk.LabelFrame(parent, text=TEXT_HISTORY_TITLE, padding=PADX_DEFAULT)
        history_frame.pack(fill=tk.BOTH, expand=True)
        
        # Создаем Canvas для реализации прокрутки
        self.canvas = tk.Canvas(history_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Создаем окно в Canvas для scrollable_frame
        self.scrollable_frame_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        def configure_scrollable_frame(event):
            """
            Обработчик изменения размера Canvas.
            
            Настраивает ширину прокручиваемой области равной ширине Canvas
            и обновляет область прокрутки.
            """
            # Устанавливаем ширину прокручиваемой области равной ширине Canvas
            self.canvas.itemconfig(self.scrollable_frame_id, width=event.width)
            # Обновляем область прокрутки
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Привязываем обработчики событий
        self.scrollable_frame.bind("<Configure>", 
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", configure_scrollable_frame)
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Размещаем Canvas и Scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Привязываем прокрутку колесиком мыши
        self._bind_mouse_scroll(self.canvas)
        
        # Инициализируем контейнер для карточек годов
        self.cards_container = self.scrollable_frame
    
    def _bind_mouse_scroll(self, widget):
        """
        Привязать прокрутку колесиком мыши к виджету.
        
        Обрабатывает различные события прокрутки для разных платформ:
        - Windows/macOS: <MouseWheel>
        - Linux: <Button-4> (вверх), <Button-5> (вниз)
        """
        # Обработка колесика мыши для Windows и macOS
        widget.bind("<MouseWheel>", self._on_mouse_scroll)
        
        # Обработка колесика мыши для Linux
        widget.bind("<Button-4>", self._on_mouse_scroll_linux)
        widget.bind("<Button-5>", self._on_mouse_scroll_linux)
        
        # Распространяем привязку на все дочерние виджеты
        self._bind_mouse_scroll_to_children(widget)
    
    def _bind_mouse_scroll_to_children(self, parent):
        """
        Рекурсивно привязать прокрутку колесиком мыши ко всем дочерним виджетам.
        
        Args:
            parent: Родительский виджет
        """
        for child in parent.winfo_children():
            child.bind("<MouseWheel>", self._on_mouse_scroll)
            child.bind("<Button-4>", self._on_mouse_scroll_linux)
            child.bind("<Button-5>", self._on_mouse_scroll_linux)
            # Рекурсивно привязываем к вложенным виджетам
            self._bind_mouse_scroll_to_children(child)
    
    def _on_mouse_scroll(self, event):
        """
        Обработчик прокрутки колесиком мыши для Windows/macOS.
        
        Args:
            event: Событие мыши с полем delta (положительное - вверх, отрицательное - вниз)
            
        Returns:
            str: "break" для предотвращения дальнейшей обработки события
        """
        # Определяем направление прокрутки
        scroll_amount = -1 if event.delta > 0 else 1
        # Прокручиваем Canvas
        self.canvas.yview_scroll(scroll_amount, "units")
        return "break"  # Предотвращаем дальнейшую обработку события
    
    def _on_mouse_scroll_linux(self, event):
        """
        Обработчик прокрутки колесиком мыши для Linux.
        
        Args:
            event: Событие мыши с полем num (4 - вверх, 5 - вниз)
            
        Returns:
            str: "break" для предотвращения дальнейшей обработки события
        """
        # В Linux event.num содержит номер кнопки: 4 - вверх, 5 - вниз
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        return "break"  # Предотвращаем дальнейшую обработку события
    
    def display_years(self, years_data: List[Dict[str, Any]]):
        """
        Отобразить карточки годов на основе полученных данных.
        
        Args:
            years_data: Список словарей с данными по годам
            
        Производительность:
            - Очистка виджетов происходит перед созданием новых
            - При большом количестве лет (>10) используется виртуализация через Canvas
            - Цвета загружаются один раз для всех карточек
        """
        # Очищаем контейнер от старых карточек
        for widget in self.cards_container.winfo_children():
            widget.destroy()

        # Загружаем цвета из настроек (или используем значения по умолчанию)
        self._advance_color = SettingsRepository.get_setting('advance_color', DEFAULT_ADVANCE_COLOR)
        self._salary_color = SettingsRepository.get_setting('salary_color', DEFAULT_SALARY_COLOR)
        self._total_color = SettingsRepository.get_setting('total_color', DEFAULT_TOTAL_COLOR)
        self._history_layout_mode = self._get_history_layout_mode()
        self._main_stats_layout_mode = self._get_main_stats_layout_mode()
        self._month_title_font_size = self._get_font_size_setting('month_title_font_size', DEFAULT_MONTH_TITLE_FONT_SIZE)
        self._month_total_font_size = self._get_font_size_setting('month_total_font_size', DEFAULT_MONTH_TOTAL_FONT_SIZE)
        self._month_data_font_size = self._get_font_size_setting('month_data_font_size', DEFAULT_MONTH_DATA_FONT_SIZE)
        
        # Проверка на наличие данных
        if not years_data:
            # Показываем сообщение, что нет данных
            no_data_label = ttk.Label(self.cards_container, text="Нет данных", font=('Segoe UI', 12))
            no_data_label.pack(pady=50)
            return
        
        # Сортируем годы по убыванию (новые сверху)
        years_data.sort(key=lambda x: x['year'], reverse=True)

        # Сбрасываем сетку карточек перед применением нового режима отображения.
        # Иначе после режима 2-колонок при возврате к 1 колонке ширина делится пополам.
        for col in range(2):
            self.cards_container.columnconfigure(col, weight=0, minsize=0, uniform="")

        # Настраиваем сетку карточек: стандартный режим или 2 карточки в ряд
        cards_per_row = 2 if self._history_layout_mode == "quarterly" else 1
        for col in range(cards_per_row):
            self.cards_container.columnconfigure(col, weight=1, uniform="year_cards")

        # Создаем карточку для каждого года
        for index, year_data in enumerate(years_data):
            row = index // cards_per_row
            col = index % cards_per_row
            self._create_year_card(year_data, row, col)
        
        # После создания карточек обновляем привязку прокрутки колесиком
        self._bind_mouse_scroll_to_children(self.cards_container)
    
    def _create_year_card(self, year_data: Dict[str, Any], row: int, col: int):
        """
        Создать карточку для одного года с данными.
        
        Args:
            year_data: Словарь с данными за год (год, сводка, месяцы)
            
        Структура карточки:
            1. Заголовок с годом и кнопками управления
            2. Статистика за год (общий доход, среднемесячный, количество месяцев)
            3. Помесячная разбивка в виде сетки 6x2
        """
        # Основной фрейм карточки с визуальными границами
        card = ttk.Frame(self.cards_container, relief="groove", borderwidth=2, padding=10)
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=10)
        
        # Заголовок карточки: год и кнопки управления
        header_frame = ttk.Frame(card)
        header_frame.pack(fill=tk.X)
        
        # Название года
        year = year_data['year']
        year_label = ttk.Label(header_frame, text=f"{year} год", font=('Segoe UI', 14, 'bold'))
        year_label.pack(side=tk.LEFT)
        
        # Контейнер для кнопок справа
        buttons_frame = ttk.Frame(header_frame)
        buttons_frame.pack(side=tk.RIGHT)
        
        # Кнопка редактирования (открывает диалог для января этого года)
        edit_button = ttk.Button(
            buttons_frame,
            text=TEXT_EDIT,
            command=lambda y=year: self._edit_year(y),
            width=16
        )
        edit_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Кнопка удаления года (с стилем для опасных действий)
        delete_button = ttk.Button(
            buttons_frame,
            text=TEXT_DELETE_YEAR,
            command=lambda y=year: self._delete_year(y),
            width=16,
            style="Danger.TButton"
        )
        delete_button.pack(side=tk.LEFT)
        
        # Разделитель 1
        separator1 = ttk.Separator(card, orient='horizontal')
        separator1.pack(fill=tk.X, pady=10)
        
        # Статистика за год - используем grid для равномерного распределения
        summary = year_data['summary']
        stats_frame = ttk.Frame(card)
        stats_frame.pack(fill=tk.X, pady=5)

        if self._main_stats_layout_mode == "column":
            # Режим статистики в столбец.
            total_income_label = ttk.Label(stats_frame, text=f"Общий доход: {MoneyUtils.format_amount(summary['total'], '')}", font=('Segoe UI', 10))
            total_income_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 2))

            avg_income_label = ttk.Label(stats_frame, text=f"Среднемесячный: {MoneyUtils.format_amount(summary['average_monthly'], '')}", font=('Segoe UI', 10))
            avg_income_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 2))

            months_with_data_label = ttk.Label(stats_frame, text=f"Месяцев с данными: {summary['months_with_data']}", font=('Segoe UI', 10))
            months_with_data_label.grid(row=2, column=0, sticky=tk.W)
        else:
            # В стандартной широкой карточке показываем статистику в строку.
            stats_frame.columnconfigure(0, weight=1)
            stats_frame.columnconfigure(1, weight=1)
            stats_frame.columnconfigure(2, weight=1)

            total_income_label = ttk.Label(stats_frame, text=f"Общий доход: {MoneyUtils.format_amount(summary['total'], '')}", font=('Segoe UI', 10))
            total_income_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

            avg_income_label = ttk.Label(stats_frame, text=f"Среднемесячный: {MoneyUtils.format_amount(summary['average_monthly'], '')}", font=('Segoe UI', 10))
            avg_income_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))

            months_with_data_label = ttk.Label(stats_frame, text=f"Месяцев с данными: {summary['months_with_data']}", font=('Segoe UI', 10))
            months_with_data_label.grid(row=0, column=2, sticky=tk.W)
        
        # Разделитель 2
        separator2 = ttk.Separator(card, orient='horizontal')
        separator2.pack(fill=tk.X, pady=10)
        
        # Помесячная разбивка
        months_label = ttk.Label(card, text="Помесячная разбивка:", font=('Segoe UI', 11, 'bold'))
        months_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Сетка месяцев - режим задается настройкой.
        months_grid = ttk.Frame(card)
        months_grid.pack(fill=tk.X, expand=False)

        if self._history_layout_mode == "quarterly":
            rows_count = 4
            cols_count = 3
            row_minsize = 72
            col_minsize = 80
        else:
            rows_count = 2
            cols_count = 6
            row_minsize = 80
            col_minsize = 100

        for i in range(rows_count):
            months_grid.grid_rowconfigure(i, weight=1, minsize=row_minsize)
        for j in range(cols_count):
            months_grid.grid_columnconfigure(j, weight=1, minsize=col_minsize, uniform="month_columns")

        # Заполняем сетку месяцами
        months = year_data['months']
        for i in range(rows_count):
            for j in range(cols_count):
                idx = i * cols_count + j
                if idx < 12:  # Всего 12 месяцев
                    month_info = months[idx]
                    self._create_month_cell(months_grid, month_info, i, j)

    def _get_history_layout_mode(self) -> str:
        """Получить режим отображения истории с валидацией."""
        mode = str(SettingsRepository.get_setting('history_layout_mode', DEFAULT_HISTORY_LAYOUT_MODE)).strip().lower()
        if mode in ("standard", "quarterly"):
            return mode
        return DEFAULT_HISTORY_LAYOUT_MODE

    def _get_main_stats_layout_mode(self) -> str:
        """Получить режим отображения блока статистики на главной вкладке."""
        mode = str(
            SettingsRepository.get_setting('main_stats_layout_mode', DEFAULT_MAIN_STATS_LAYOUT_MODE)
        ).strip().lower()
        if mode in ("row", "column"):
            return mode
        return DEFAULT_MAIN_STATS_LAYOUT_MODE

    @staticmethod
    def _get_font_size_setting(key: str, default: int) -> int:
        """Безопасно получить размер шрифта из настроек."""
        raw_value = SettingsRepository.get_setting(key, default)
        try:
            value = int(str(raw_value).strip())
        except (TypeError, ValueError):
            value = default
        return max(7, min(24, value))
    
    def _create_month_cell(self, parent, month_info: Dict[str, Any], row: int, col: int):
        """
        Создать ячейку месяца в сетке.
        
        Args:
            parent: Родительский виджет (сетка месяцев)
            month_info: Данные месяца (название, суммы, даты)
            row: Строка в сетке (0 или 1)
            col: Столбец в сетке (0-5)
            
        Визуальное представление:
            - Месяц с данными: суммы аванса и зарплаты с цветным оформлением
            - Месяц без данных: серый текст "Нет данных"
            - Даты выплат отображаются если указаны
        """
        # Получаем цвет фона для совместимости с темой
        style = ttk.Style()
        bg = style.lookup("TFrame", "background") or self.winfo_toplevel().cget("bg")

        # Фрейм ячейки с границами
        cell = tk.Frame(parent, relief="solid", borderwidth=1, bg=bg)
        cell.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
        
        # Название месяца жирным шрифтом
        month_name = month_info['month_name']
        month_label = tk.Label(cell, text=month_name, font=('Segoe UI', self._month_title_font_size, 'bold'), bg=bg)
        month_label.pack(anchor=tk.CENTER, pady=(2, 1))
        
        # Если есть данные за месяц, показываем их
        if month_info['has_data']:
            advance = month_info['advance']
            salary = month_info['salary']
            total = month_info['total']
            advance_date = month_info.get('advance_date') or ""
            salary_date = month_info.get('salary_date') or ""

            # Фиксированная по высоте зона выплат — чтобы "Итого" не сдвигалось
            payments_area_height = max(58, 6 * self._month_data_font_size + 10)
            payments_area = tk.Frame(cell, bg=bg, height=payments_area_height)
            payments_area.pack(fill=tk.X, padx=3, pady=(0, 2))
            payments_area.pack_propagate(False)

            # Блок табличного отображения выплат: "Дата - Сумма"
            payments_frame = tk.Frame(payments_area, bg=bg)
            payments_frame.pack(fill=tk.X, anchor="n")
            # Растягиваем табличные колонки по ширине карточки:
            # дата и сумма занимают все доступное пространство.
            payments_frame.grid_columnconfigure(0, weight=0, minsize=54)  # Название выплаты
            payments_frame.grid_columnconfigure(1, weight=1, minsize=52)  # Дата (растягивается)
            payments_frame.grid_columnconfigure(2, weight=1, minsize=56)  # Сумма (растягивается)

            header_date_label = tk.Label(
                payments_frame,
                text="Дата",
                font=('Segoe UI', self._month_data_font_size, 'bold'),
                bg=bg
            )
            header_date_label.grid(row=0, column=1, sticky="e", padx=(2, 1))

            header_sum_label = tk.Label(
                payments_frame,
                text="Сумма",
                font=('Segoe UI', self._month_data_font_size, 'bold'),
                bg=bg
            )
            header_sum_label.grid(row=0, column=2, sticky="e", padx=(1, 1))

            data_row = 1

            # Отображение аванса (если сумма > 0)
            if advance > 0:
                advance_name_label = tk.Label(
                    payments_frame,
                    text="Аванс",
                    font=('Segoe UI', self._month_data_font_size),
                    fg=self._advance_color,
                    bg=bg
                )
                advance_name_label.grid(row=data_row, column=0, sticky="w")

                advance_date_label = tk.Label(
                    payments_frame,
                    text=advance_date or "-",
                    font=('Segoe UI', self._month_data_font_size),
                    fg=self._advance_color,
                    bg=bg
                )
                advance_date_label.grid(row=data_row, column=1, sticky="e", padx=(2, 1))

                advance_amount_label = tk.Label(
                    payments_frame,
                    text=MoneyUtils.format_amount(advance, ''),
                    font=('Segoe UI', self._month_data_font_size),
                    fg=self._advance_color,
                    bg=bg
                )
                advance_amount_label.grid(row=data_row, column=2, sticky="e", padx=(1, 1))

                data_row += 1

            # Отображение зарплаты (если сумма > 0)
            if salary > 0:
                salary_name_label = tk.Label(
                    payments_frame,
                    text="Зарплата",
                    font=('Segoe UI', self._month_data_font_size),
                    fg=self._salary_color,
                    bg=bg
                )
                salary_name_label.grid(row=data_row, column=0, sticky="w")

                salary_date_label = tk.Label(
                    payments_frame,
                    text=salary_date or "-",
                    font=('Segoe UI', self._month_data_font_size),
                    fg=self._salary_color,
                    bg=bg
                )
                salary_date_label.grid(row=data_row, column=1, sticky="e", padx=(2, 1))

                salary_amount_label = tk.Label(
                    payments_frame,
                    text=MoneyUtils.format_amount(salary, ''),
                    font=('Segoe UI', self._month_data_font_size),
                    fg=self._salary_color,
                    bg=bg
                )
                salary_amount_label.grid(row=data_row, column=2, sticky="e", padx=(1, 1))

            # Итоговая сумма за месяц
            total_label = tk.Label(
                cell,
                text=f"Итого: {MoneyUtils.format_amount(total, '')}",
                font=('Segoe UI', self._month_total_font_size, 'bold'),
                fg=self._total_color,
                bg=bg
            )
            total_label.pack(side=tk.BOTTOM, anchor=tk.CENTER, pady=(3, 2))
        else:
            # Нет данных за этот месяц
            no_data_label = tk.Label(cell, text="Нет данных", font=('Segoe UI', 9, 'italic'), fg='gray', bg=bg)
            no_data_label.pack(expand=True, anchor=tk.CENTER)
    
    def _edit_year(self, year: int):
        """Обработка нажатия кнопки редактирования года"""
        # Открываем диалог для января этого года через контроллер
        self.controller.edit_year(year)
    
    def _delete_year(self, year: int):
        """
        Обработка нажатия кнопки удаления года.
        
        Args:
            year: Год для удаления
            
        Внимание:
            - Удаление всех данных за год - необратимая операция
            - Контроллер покажет диалог подтверждения перед удалением
        """
        # Вызываем метод контроллера для удаления года
        self.controller.delete_year(year)
    
    def update_statistics(self, stats: Dict[str, Any]):
        """
        Обновить статистику (метод оставлен для совместимости).
        
        Args:
            stats: Статистические данные
            
        Примечание:
            - Метод больше не отображает статистику на главной вкладке
            - Оставлен для обратной совместимости с контроллером
            - Статистика теперь показывается на вкладке аналитики
        """
        # Этот метод больше не отображает статистику на главной вкладке
        # Оставлен для совместимости с контроллером
        pass

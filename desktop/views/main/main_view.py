"""
Главное представление (View) приложения.

Отображает историю заработной платы в виде карточек по годам
с помесячной детализацией. Реализует паттерн View в архитектуре MVC.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any
from desktop.views.base_view import BaseView
from desktop.views.dialogs.about_dialog import AboutDialog
from desktop.views.constants import (
    PADX_DEFAULT, PADY_DEFAULT,
    TEXT_ACTIONS, TEXT_ADD_DATA, TEXT_REFRESH_HISTORY, TEXT_EXPORT_HISTORY, TEXT_BACKUP,
    TEXT_EDIT, TEXT_DELETE_YEAR, TEXT_HISTORY_TITLE, ABOUT_FRAME_TITLE,
    WINDOW_MAIN_MIN_WIDTH, WINDOW_MAIN_MIN_HEIGHT,
    WINDOW_MAIN_DEFAULT_WIDTH, WINDOW_MAIN_DEFAULT_HEIGHT,
    DEFAULT_HISTORY_LAYOUT_MODE, DEFAULT_MAIN_STATS_LAYOUT_MODE,
    DEFAULT_MONTH_TITLE_FONT_SIZE, DEFAULT_MONTH_TOTAL_FONT_SIZE, DEFAULT_MONTH_DATA_FONT_SIZE,
    CARD_BUTTON_WIDTH, FONT_YEAR_TITLE, FONT_CARD_STATS, FONT_CARD_SECTION,
    FONT_NO_DATA, FONT_MONTH_NO_DATA
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

        # Кнопка "О программе" — справа, отдельно от действий с данными
        self.about_button = ttk.Button(
            button_container,
            text=ABOUT_FRAME_TITLE,
            command=self._show_about
        )
        self.about_button.pack(side=tk.RIGHT)

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
            no_data_label = ttk.Label(self.cards_container, text="Нет данных", font=FONT_NO_DATA)
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
            row: Строка в сетке карточек
            col: Столбец в сетке карточек

        Структура карточки:
            1. Заголовок с годом и кнопками управления
            2. Статистика за год (общий доход, среднемесячный, количество месяцев)
            3. Помесячная разбивка
        """
        # Основной фрейм карточки с тонкой рамкой
        card = ttk.Frame(self.cards_container, relief="solid", borderwidth=1, padding=10)
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=10)

        # Заголовок (год + кнопки управления)
        self._create_card_header(card, year_data['year'])

        # Разделитель между заголовком и статистикой
        ttk.Separator(card, orient='horizontal').pack(fill=tk.X, pady=10)

        # Статистика за год
        self._create_year_stats(card, year_data['summary'])

        # Подзаголовок помесячной разбивки (визуально отделяет блок без доп. разделителя)
        ttk.Label(card, text="Помесячная разбивка:", font=FONT_CARD_SECTION).pack(
            anchor=tk.W, pady=(10, 10)
        )

        # Сетка месяцев
        self._create_months_grid(card, year_data['months'])

    def _create_card_header(self, card, year: int):
        """Создать заголовок карточки: год слева, кнопки управления справа."""
        header_frame = ttk.Frame(card)
        header_frame.pack(fill=tk.X)

        # Название года
        ttk.Label(header_frame, text=f"{year} год", font=FONT_YEAR_TITLE).pack(side=tk.LEFT)

        # Контейнер для кнопок справа
        buttons_frame = ttk.Frame(header_frame)
        buttons_frame.pack(side=tk.RIGHT)

        # Кнопка редактирования (открывает диалог для января этого года)
        edit_button = ttk.Button(
            buttons_frame,
            text=TEXT_EDIT,
            command=lambda y=year: self._edit_year(y),
            width=CARD_BUTTON_WIDTH
        )
        edit_button.pack(side=tk.LEFT, padx=(0, 5))

        # Кнопка удаления года (стиль для опасных действий)
        delete_button = ttk.Button(
            buttons_frame,
            text=TEXT_DELETE_YEAR,
            command=lambda y=year: self._delete_year(y),
            width=CARD_BUTTON_WIDTH,
            style="Danger.TButton"
        )
        delete_button.pack(side=tk.LEFT)

    def _create_year_stats(self, card, summary: Dict[str, Any]):
        """Создать блок статистики за год (в строку или столбцом по настройке)."""
        stats_frame = ttk.Frame(card)
        stats_frame.pack(fill=tk.X, pady=5)

        total_text = f"Общий доход: {MoneyUtils.format_amount(summary['total'], '')}"
        avg_text = f"Среднемесячный: {MoneyUtils.format_amount(summary['average_monthly'], '')}"
        months_text = f"Месяцев с данными: {summary['months_with_data']}"

        if self._main_stats_layout_mode == "column":
            # Режим статистики в столбец.
            ttk.Label(stats_frame, text=total_text, font=FONT_CARD_STATS).grid(
                row=0, column=0, sticky=tk.W, pady=(0, 2))
            ttk.Label(stats_frame, text=avg_text, font=FONT_CARD_STATS).grid(
                row=1, column=0, sticky=tk.W, pady=(0, 2))
            ttk.Label(stats_frame, text=months_text, font=FONT_CARD_STATS).grid(
                row=2, column=0, sticky=tk.W)
        else:
            # В стандартной широкой карточке показываем статистику в строку.
            stats_frame.columnconfigure(0, weight=1)
            stats_frame.columnconfigure(1, weight=1)
            stats_frame.columnconfigure(2, weight=1)

            ttk.Label(stats_frame, text=total_text, font=FONT_CARD_STATS).grid(
                row=0, column=0, sticky=tk.W, padx=(0, 10))
            ttk.Label(stats_frame, text=avg_text, font=FONT_CARD_STATS).grid(
                row=0, column=1, sticky=tk.W, padx=(0, 10))
            ttk.Label(stats_frame, text=months_text, font=FONT_CARD_STATS).grid(
                row=0, column=2, sticky=tk.W)

    def _create_months_grid(self, card, months: List[Dict[str, Any]]):
        """Создать сетку из 12 ячеек месяцев (режим задаётся настройкой)."""
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
        for i in range(rows_count):
            for j in range(cols_count):
                idx = i * cols_count + j
                if idx < 12:  # Всего 12 месяцев
                    self._create_month_cell(months_grid, months[idx], i, j)

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
            row: Строка в сетке
            col: Столбец в сетке

        Визуальное представление:
            - Месяц с данными: суммы аванса и зарплаты с цветным оформлением
            - Месяц без данных: серый текст "Нет данных"
        """
        # Получаем цвет фона для совместимости с темой
        style = ttk.Style()
        bg = style.lookup("TFrame", "background") or self.winfo_toplevel().cget("bg")

        # Фрейм ячейки с тонкой рамкой
        cell = tk.Frame(parent, relief="solid", borderwidth=1, bg=bg)
        cell.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")

        # Название месяца жирным шрифтом
        month_label = tk.Label(cell, text=month_info['month_name'],
                               font=('Segoe UI', self._month_title_font_size, 'bold'), bg=bg)
        month_label.pack(anchor=tk.CENTER, pady=(2, 1))

        if month_info['has_data']:
            # Таблица выплат (аванс/зарплата) и итог за месяц
            self._create_payments_table(cell, month_info, bg)

            total_label = tk.Label(
                cell,
                text=f"Итого: {MoneyUtils.format_amount(month_info['total'], '')}",
                font=('Segoe UI', self._month_total_font_size, 'bold'),
                fg=self._total_color,
                bg=bg
            )
            total_label.pack(side=tk.BOTTOM, anchor=tk.CENTER, pady=(3, 2))
        else:
            # Нет данных за этот месяц
            no_data_label = tk.Label(cell, text="Нет данных", font=FONT_MONTH_NO_DATA, fg='gray', bg=bg)
            no_data_label.pack(expand=True, anchor=tk.CENTER)

    def _create_payments_table(self, cell, month_info: Dict[str, Any], bg):
        """
        Построить компактную таблицу выплат месяца: строки «Аванс»/«Зарплата»
        с датой и суммой. Зона выплат имеет фиксированную высоту (до 2 строк),
        чтобы строка «Итого» не сдвигалась между ячейками.
        """
        advance = month_info['advance']
        salary = month_info['salary']
        advance_date = month_info.get('advance_date') or ""
        salary_date = month_info.get('salary_date') or ""

        # Фиксированная по высоте зона выплат (до 2 строк)
        payments_area_height = max(44, 2 * (self._month_data_font_size + 9) + 4)
        payments_area = tk.Frame(cell, bg=bg, height=payments_area_height)
        payments_area.pack(fill=tk.X, padx=4, pady=(0, 2))
        payments_area.pack_propagate(False)

        payments_frame = tk.Frame(payments_area, bg=bg)
        payments_frame.pack(fill=tk.X, anchor="n")
        # Колонки: название выплаты, дата (растягивается), сумма (растягивается)
        payments_frame.grid_columnconfigure(0, weight=0, minsize=54)
        payments_frame.grid_columnconfigure(1, weight=1, minsize=52)
        payments_frame.grid_columnconfigure(2, weight=1, minsize=56)

        data_row = 0
        if advance > 0:
            self._add_payment_row(payments_frame, data_row, "Аванс", advance_date, advance, self._advance_color, bg)
            data_row += 1
        if salary > 0:
            self._add_payment_row(payments_frame, data_row, "Зарплата", salary_date, salary, self._salary_color, bg)

    def _add_payment_row(self, parent, row: int, name: str, date: str, amount: float, color: str, bg):
        """Добавить строку выплаты «Название | Дата | Сумма» в таблицу выплат."""
        font = ('Segoe UI', self._month_data_font_size)

        tk.Label(parent, text=name, font=font, fg=color, bg=bg).grid(
            row=row, column=0, sticky="w")
        tk.Label(parent, text=date or "-", font=font, fg=color, bg=bg).grid(
            row=row, column=1, sticky="e", padx=(2, 1))
        tk.Label(parent, text=MoneyUtils.format_amount(amount, ''), font=font, fg=color, bg=bg).grid(
            row=row, column=2, sticky="e", padx=(1, 1))

    def _show_about(self):
        """Открыть модальное окно «О программе»."""
        AboutDialog(self.winfo_toplevel())

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

"""
Главное представление (View) приложения.

Отображает историю заработной платы в виде карточек по годам
с помесячной детализацией. Реализует паттерн View в архитектуре MVC.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional
from desktop.views.base_view import BaseView
from desktop.views.dialogs.about_dialog import AboutDialog
from desktop.views.constants import (
    PADX_DEFAULT, PADY_DEFAULT,
    TEXT_ACTIONS, TEXT_ADD_DATA, TEXT_REFRESH_HISTORY, TEXT_EXPORT_HISTORY, TEXT_BACKUP,
    TEXT_EDIT, TEXT_DELETE_YEAR, TEXT_HISTORY_TITLE, ABOUT_FRAME_TITLE,
    TEXT_MONTHS_SECTION, ARROW_YEAR_EXPANDED, ARROW_YEAR_COLLAPSED,
    DEFAULT_HISTORY_LAYOUT_MODE, DEFAULT_MAIN_STATS_LAYOUT_MODE,
    DEFAULT_MONTH_TITLE_FONT_SIZE, DEFAULT_MONTH_TOTAL_FONT_SIZE, DEFAULT_MONTH_DATA_FONT_SIZE,
    CARD_BUTTON_WIDTH, FONT_YEAR_TITLE, FONT_YEAR_ARROW, FONT_CARD_STATS, FONT_CARD_SECTION,
    FONT_NO_DATA
)
from core.utils.money import MoneyUtils
from desktop.views.constants import DEFAULT_ADVANCE_COLOR, DEFAULT_SALARY_COLOR, DEFAULT_TOTAL_COLOR
from desktop.views.main.month_cell import MonthCell, MonthCellStyle
from desktop.widgets.auto_hide_scrollbar import AutoHideScrollbar


class MainView(BaseView):
    """Класс главной вкладки с отображением истории зарплат по годам"""

    def __init__(self, parent, controller):
        # Развёрнутые годы: выбор пользователя сохраняется до закрытия приложения
        self._expanded_years: set[int] = set()
        # Годы, уже показанные в этом сеансе (новый год по умолчанию разворачивается)
        self._known_years: set[int] = set()
        # Карточки текущей отрисовки (по порядку лет): год -> {"card", "body", "arrow", "months", "built"}
        self._year_cards: Dict[int, Dict[str, Any]] = {}
        # Колонки, по которым раскладываются карточки (1 или 2 по режиму истории)
        self._card_columns: List[ttk.Frame] = []
        super().__init__(parent, controller)

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

        # Создаем Canvas для реализации прокрутки.
        # Фон как у панели: под свёрнутыми годами остаётся свободное место.
        self.canvas = tk.Canvas(
            history_frame,
            highlightthickness=0,
            bg=ttk.Style().lookup("TFrame", "background") or None,
        )
        # Полоса прокрутки видна, только когда карточки не помещаются
        self.scrollbar = AutoHideScrollbar(history_frame, orient="vertical", command=self.canvas.yview)
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
            self._update_scroll_region()

        # Привязываем обработчики событий
        self.scrollable_frame.bind("<Configure>", lambda e: self._update_scroll_region())
        self.canvas.bind("<Configure>", configure_scrollable_frame)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Размещаем Canvas и Scrollbar (grid нужен AutoHideScrollbar для скрытия)
        history_frame.grid_rowconfigure(0, weight=1)
        history_frame.grid_columnconfigure(0, weight=1)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Привязываем прокрутку колесиком мыши
        self._bind_mouse_scroll(self.canvas)

        # Инициализируем контейнер для карточек годов
        self.cards_container = self.scrollable_frame

    def _update_scroll_region(self) -> None:
        """
        Обновить область прокрутки под содержимое.

        Высота области не меньше видимой высоты Canvas: если содержимое
        короче окна, Tk разрешает двигать его внутри окна, и колёсико
        сдвигало карточки вниз, оставляя пустоту сверху.
        """
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        _x1, _y1, x2, y2 = bbox
        height = max(y2, self.canvas.winfo_height())
        self.canvas.configure(scrollregion=(0, 0, x2, height))

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

    def display_years(
        self,
        years_data: List[Dict[str, Any]],
        default_expanded_year: Optional[int] = None,
    ):
        """
        Отобразить карточки годов на основе полученных данных.

        Args:
            years_data: Список словарей с данными по годам
            default_expanded_year: Год, который разворачивается при первом
                появлении (остальные годы показываются свёрнутыми)

        Производительность:
            - Свёрнутый год показывает только заголовок и итоги; сетка
              месяцев строится при первом разворачивании
            - Шрифты и цвета ячеек создаются один раз для всех карточек
        """
        # Очищаем контейнер от старых карточек
        for widget in self.cards_container.winfo_children():
            widget.destroy()
        self._year_cards = {}

        if not hasattr(self, "_history_layout_mode"):
            self.apply_settings({})

        # Проверка на наличие данных
        if not years_data:
            # Показываем сообщение, что нет данных
            no_data_label = ttk.Label(self.cards_container, text="Нет данных", font=FONT_NO_DATA)
            no_data_label.pack(pady=50)
            return

        # Сортируем годы по убыванию (новые сверху), не изменяя переданный список
        years_data = sorted(years_data, key=lambda x: x['year'], reverse=True)

        self._remember_expanded_years(years_data, default_expanded_year)

        # Шрифты и цвета ячеек месяцев — один раз на всю отрисовку
        self._cell_style = self._create_cell_style()

        # Сбрасываем сетку карточек перед применением нового режима отображения.
        # Иначе после режима 2-колонок при возврате к 1 колонке ширина делится пополам.
        for col in range(2):
            self.cards_container.columnconfigure(col, weight=0, minsize=0, uniform="")

        # Колонки карточек: стандартный режим — одна, «по кварталам» — две
        columns_count = 2 if self._history_layout_mode == "quarterly" else 1
        self._card_columns = []
        for col in range(columns_count):
            self.cards_container.columnconfigure(col, weight=1, uniform="year_cards")
            column = ttk.Frame(self.cards_container)
            column.grid(row=0, column=col, sticky="new")
            self._card_columns.append(column)

        # Создаем карточку для каждого года и раскладываем карточки по колонкам
        for year_data in years_data:
            self._create_year_card(year_data)
        self._arrange_cards()

        # После создания карточек обновляем привязку прокрутки колесиком
        self._bind_mouse_scroll_to_children(self.cards_container)

    def _remember_expanded_years(
        self, years_data: List[Dict[str, Any]], default_expanded_year: Optional[int]
    ) -> None:
        """
        Обновить набор развёрнутых годов перед отрисовкой.

        Год по умолчанию разворачивается, только когда появляется впервые
        за сеанс: если пользователь его свернул, выбор сохраняется при
        следующих перерисовках (после сохранения данных, смены настроек).
        """
        if default_expanded_year is not None and default_expanded_year not in self._known_years:
            self._expanded_years.add(default_expanded_year)
        self._known_years.update(int(item['year']) for item in years_data)

    def _create_year_card(self, year_data: Dict[str, Any]):
        """
        Создать карточку для одного года с данными (размещает её _arrange_cards).

        Args:
            year_data: Словарь с данными за год (год, сводка, месяцы)

        Структура карточки:
            1. Заголовок: стрелка и год (клик сворачивает/разворачивает), кнопки управления
            2. Статистика за год (общий доход, среднемесячный, количество месяцев)
            3. Помесячная разбивка — только у развёрнутого года
        """
        year = int(year_data['year'])

        # Основной фрейм карточки с тонкой рамкой
        card = ttk.Frame(self.cards_container, relief="solid", borderwidth=1, padding=10)

        # Заголовок (стрелка + год + кнопки управления)
        arrow = self._create_card_header(card, year)

        # Разделитель между заголовком и статистикой
        ttk.Separator(card, orient='horizontal').pack(fill=tk.X, pady=10)

        # Статистика за год (видна и у свёрнутого года)
        self._create_year_stats(card, year_data['summary'])

        # Помесячная разбивка: контейнер создаётся сразу, содержимое — при первом разворачивании
        self._year_cards[year] = {
            "card": card,
            "body": ttk.Frame(card),
            "arrow": arrow,
            "months": year_data['months'],
            "built": False,
        }
        self._set_year_expanded(year, year in self._expanded_years, arrange=False)

    def _arrange_cards(self) -> None:
        """
        Разложить карточки по колонкам: каждая следующая — в самую короткую.

        В режиме «по кварталам» свёрнутые годы встают рядом с развёрнутым,
        без пустот. Порядок лет сверху вниз сохраняется, а карточка, которую
        сворачивают или разворачивают, остаётся в своей колонке: её место
        зависит только от карточек выше, сдвигаются лишь следующие годы.
        """
        # Актуальные высоты карточек (в т.ч. только что развёрнутой)
        self.cards_container.update_idletasks()
        cards = [item["card"] for item in self._year_cards.values()]
        card_heights = [card.winfo_reqheight() for card in cards]

        column_heights = [0] * len(self._card_columns)
        for card in cards:
            card.pack_forget()
        for card, height in zip(cards, card_heights):
            column_index = column_heights.index(min(column_heights))
            card.pack(in_=self._card_columns[column_index], fill=tk.X, padx=5, pady=10)
            column_heights[column_index] += height

    def _toggle_year(self, year: int) -> None:
        """Свернуть или развернуть год по клику на его заголовок."""
        self._set_year_expanded(year, year not in self._expanded_years)

    def _set_year_expanded(self, year: int, expanded: bool, arrange: bool = True) -> None:
        """
        Показать или скрыть помесячную разбивку года.

        Args:
            arrange: Пересчитать раскладку карточек по колонкам (не нужно,
                пока карточки ещё создаются в display_years)
        """
        entry = self._year_cards[year]
        if expanded:
            if not entry["built"]:
                self._create_months_section(entry["body"], year, entry["months"])
                self._bind_mouse_scroll_to_children(entry["body"])
                entry["built"] = True
            entry["body"].pack(fill=tk.X)
            self._expanded_years.add(year)
        else:
            # Сетка остаётся построенной: повторное разворачивание мгновенное
            entry["body"].pack_forget()
            self._expanded_years.discard(year)
        entry["arrow"].configure(text=ARROW_YEAR_EXPANDED if expanded else ARROW_YEAR_COLLAPSED)
        if arrange:
            self._arrange_cards()

    def _create_months_section(self, parent, year: int, months: List[Dict[str, Any]]) -> None:
        """Подзаголовок и сетка месяцев развёрнутого года."""
        ttk.Label(parent, text=TEXT_MONTHS_SECTION, font=FONT_CARD_SECTION).pack(
            anchor=tk.W, pady=(10, 10)
        )
        self._create_months_grid(parent, year, months)

    def _create_card_header(self, card, year: int) -> ttk.Label:
        """
        Создать заголовок карточки: стрелка и год слева, кнопки управления справа.

        Returns:
            ttk.Label: Стрелка, которая меняется при сворачивании/разворачивании
        """
        header_frame = ttk.Frame(card)
        header_frame.pack(fill=tk.X)

        # Стрелка и название года — по клику год сворачивается/разворачивается.
        # Ширина стрелки фиксирована, чтобы год не сдвигался при смене ▶/▼.
        arrow = ttk.Label(header_frame, font=FONT_YEAR_ARROW, width=2, cursor="hand2")
        arrow.pack(side=tk.LEFT)
        title = ttk.Label(header_frame, text=f"{year} год", font=FONT_YEAR_TITLE, cursor="hand2")
        title.pack(side=tk.LEFT)
        for widget in (arrow, title):
            widget.bind("<Button-1>", lambda _event, y=year: self._toggle_year(y))

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

        return arrow

    def _create_year_stats(self, card, summary: Dict[str, Any]):
        """Создать блок статистики за год (в строку или столбцом по настройке)."""
        stats_frame = ttk.Frame(card)
        stats_frame.pack(fill=tk.X, pady=5)

        total_text = f"Общий доход: {MoneyUtils.format_amount(summary['total'], '')}"
        avg_text = f"Среднемесячный: {MoneyUtils.format_amount(summary['average_monthly'], '')}"
        if float(summary.get('total_extras') or 0) > 0:
            # С доп. выплатами среднее «всего» и регулярный доход расходятся
            regular = MoneyUtils.format_amount(summary.get('regular_average_monthly') or 0, '')
            avg_text += f" (регулярный {regular})"
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

    def _create_months_grid(self, card, year: int, months: List[Dict[str, Any]]):
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
                    # Клик по месяцу открывает его в окне ввода (и пустой — для заполнения)
                    MonthCell(
                        months_grid,
                        months[idx],
                        self._cell_style,
                        on_click=lambda y=year, m=idx + 1: self._edit_month(y, m),
                    ).grid(row=i, column=j, padx=2, pady=2, sticky="nsew")

    def _create_cell_style(self) -> MonthCellStyle:
        """Собрать шрифты и цвета ячеек месяцев из текущих настроек отображения."""
        # Цвет фона под тему, чтобы ячейки сливались с карточкой
        bg = ttk.Style().lookup("TFrame", "background") or self.winfo_toplevel().cget("bg")
        return MonthCellStyle.create(
            self,
            background=bg,
            title_size=self._month_title_font_size,
            data_size=self._month_data_font_size,
            total_size=self._month_total_font_size,
            advance_color=self._advance_color,
            salary_color=self._salary_color,
            total_color=self._total_color,
        )

    def apply_settings(self, settings: Dict[str, Any]) -> None:
        """Применить подготовленные контроллером настройки отображения."""
        self._advance_color = str(settings.get("advance_color", DEFAULT_ADVANCE_COLOR))
        self._salary_color = str(settings.get("salary_color", DEFAULT_SALARY_COLOR))
        self._total_color = str(settings.get("total_color", DEFAULT_TOTAL_COLOR))

        history_mode = str(settings.get("history_layout_mode", DEFAULT_HISTORY_LAYOUT_MODE))
        self._history_layout_mode = (
            history_mode if history_mode in {"standard", "quarterly"} else DEFAULT_HISTORY_LAYOUT_MODE
        )

        stats_mode = str(settings.get("main_stats_layout_mode", DEFAULT_MAIN_STATS_LAYOUT_MODE))
        self._main_stats_layout_mode = (
            stats_mode if stats_mode in {"row", "column"} else DEFAULT_MAIN_STATS_LAYOUT_MODE
        )

        self._month_title_font_size = self._coerce_font_size(
            settings.get("month_title_font_size"), DEFAULT_MONTH_TITLE_FONT_SIZE
        )
        self._month_total_font_size = self._coerce_font_size(
            settings.get("month_total_font_size"), DEFAULT_MONTH_TOTAL_FONT_SIZE
        )
        self._month_data_font_size = self._coerce_font_size(
            settings.get("month_data_font_size"), DEFAULT_MONTH_DATA_FONT_SIZE
        )

    @staticmethod
    def _coerce_font_size(raw_value: Any, default: int) -> int:
        try:
            value = int(str(raw_value).strip())
        except (TypeError, ValueError):
            value = default
        return max(7, min(24, value))

    def _show_about(self):
        """Открыть модальное окно «О программе»."""
        AboutDialog(self.winfo_toplevel())

    def _edit_month(self, year: int, month: int):
        """Клик по ячейке месяца: открыть этот месяц в окне ввода."""
        self.controller.edit_month(year, month)

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

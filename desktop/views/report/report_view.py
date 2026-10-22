"""
Представление аналитики и отчетов.

Содержит графики и KPI-метрики для визуализации данных о зарплатах.
Использует matplotlib для построения графиков и ttk для интерфейса.
"""

import tkinter as tk
from tkinter import ttk

from desktop.views.base_view import BaseView
from desktop.presenters import ChartPresenter
from desktop.views.report.bar_chart_tooltip import BarChartTooltip
from desktop.views.constants import (
    PADX_DEFAULT, PADY_DEFAULT,
    TEXT_CHART_SETTINGS, TEXT_REFRESH_CHARTS, TEXT_ALL_YEARS, TEXT_YEAR,
    TEXT_KPI_TITLE, TEXT_KPI_TOTAL, TEXT_KPI_AVG, TEXT_KPI_BEST_MONTH,
    TEXT_KPI_BEST_YEAR, TEXT_KPI_RECORDS, TEXT_KPI_PERIOD,
    TAB_MONTHLY_DATA, TAB_YEARLY_COMPARISON, TAB_GROWTH_RATES, TAB_AVERAGE_VALUES,
    CHART_MONTHLY_TITLE, CHART_YEARLY_TITLE, CHART_GROWTH_TITLE, CHART_AVERAGE_TITLE,
    AXIS_X_MONTHS, AXIS_X_YEARS, AXIS_X_PERIODS, AXIS_Y_AMOUNT, AXIS_Y_TOTAL,
    AXIS_Y_GROWTH, AXIS_Y_AVERAGE,
    ERROR_NO_MATPLOTLIB, TEXT_NO_DATA, TEXT_LOADING_CHARTS,
    COMBOBOX_WIDTH
)


def _load_matplotlib():
    """
    Загрузить matplotlib с Tk-бэкендом.

    Импорт тяжёлый (~1 с), поэтому выполняется только при первом открытии
    вкладки аналитики, а не при запуске приложения.

    Returns:
        (FigureCanvasTkAgg, Figure) или None, если matplotlib не установлен.
    """
    try:
        import matplotlib
        matplotlib.use('TkAgg')  # Использование Tk-совместимого бэкенда
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
    except ImportError:
        return None
    return FigureCanvasTkAgg, Figure


class ReportView(BaseView):
    """Класс вкладки аналитики с графиками и KPI-метриками"""

    def __init__(self, parent, controller):
        """
        Инициализация представления аналитики.

        Args:
            parent: Родительский виджет
            controller: Контроллер навигации
        """
        self.charts = {}  # Словарь для хранения объектов графиков
        self.presenter = ChartPresenter()  # Presenter для подготовки данных графиков
        self._is_built = False
        super().__init__(parent, controller)

    def _create_widgets(self):
        """
        Создать лёгкую заглушку вкладки.

        Графики и панели строятся при первом показе вкладки (см. ensure_built),
        чтобы не замедлять запуск приложения.
        """
        self._loading_label = ttk.Label(self, text=TEXT_LOADING_CHARTS, font=('Segoe UI', 10))
        self._loading_label.pack(expand=True)

    def ensure_built(self):
        """Построить содержимое вкладки при первом обращении (повторные вызовы ничего не делают)."""
        if self._is_built:
            return
        self._is_built = True
        # Показываем «Загрузка графиков…» на время импорта matplotlib и построения графиков
        self.update_idletasks()
        try:
            self._build_widgets()
        finally:
            self._loading_label.destroy()

    def _build_widgets(self):
        """Создание всех виджетов вкладки аналитики"""
        # Основной контейнер
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=PADX_DEFAULT, pady=PADY_DEFAULT)

        # Проверка доступности matplotlib
        backend = _load_matplotlib()
        if backend is None:
            # Показать сообщение об ошибке если matplotlib не установлен
            error_frame = ttk.Frame(main_container)
            error_frame.pack(fill=tk.BOTH, expand=True)
            
            error_label = ttk.Label(
                error_frame,
                text=ERROR_NO_MATPLOTLIB,
                justify=tk.CENTER,
                font=('Segoe UI', 10)
            )
            error_label.pack(expand=True)
            return
        self._figure_canvas_cls, self._figure_cls = backend

        # Верхняя панель: управление и KPI
        top_row = ttk.Frame(main_container)
        top_row.pack(fill=tk.X)
        
        # Настройка grid для верхней панели
        top_row.grid_columnconfigure(0, weight=0)  # Панель управления (фиксированная ширина)
        top_row.grid_columnconfigure(1, weight=1)  # KPI-панель (растягивается)
        
        # Создание панели управления и KPI
        self._create_control_panel(top_row)
        self._create_kpi_panel(top_row)
        
        # Создание notebook для графиков (вкладки с графиками)
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(PADY_DEFAULT, 0))
        
        # Создание вкладок с графиками
        self._create_chart_tabs()
    
    def _create_control_panel(self, parent):
        """
        Создать панель управления графиками.
        
        Содержит:
        - Выбор года для фильтрации данных
        - Кнопку обновления графиков
        """
        control_frame = ttk.LabelFrame(parent, text=TEXT_CHART_SETTINGS, padding=(8, 6))
        control_frame.grid(row=0, column=0, sticky="nw", padx=(0, 8))
        control_frame.configure(width=240)  # Фиксированная ширина
        control_frame.grid_propagate(False)  # Запрет изменения размера
        
        # Выбор года
        year_frame = ttk.Frame(control_frame)
        year_frame.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(year_frame, text=TEXT_YEAR).pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
        
        # Combobox для выбора года
        self.year_var = tk.StringVar(value=TEXT_ALL_YEARS)
        self.year_combobox = ttk.Combobox(
            year_frame,
            textvariable=self.year_var,
            state="readonly",  # Только выбор из списка
            width=COMBOBOX_WIDTH
        )
        self.year_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Кнопка обновления графиков
        refresh_button = ttk.Button(
            control_frame,
            text=TEXT_REFRESH_CHARTS,
            command=self._refresh_charts
        )
        refresh_button.pack(anchor="e")
        
        # Привязка события выбора года к обновлению графиков
        self.year_combobox.bind("<<ComboboxSelected>>", lambda e: self._refresh_charts())

    def _create_kpi_panel(self, parent):
        """
        Создать панель быстрых итогов (KPI).
        
        Отображает ключевые метрики:
        - Период анализа
        - Количество записей
        - Общий доход
        - Средний доход
        - Лучший месяц
        - Лучший год
        - Прогноз на текущий год (только для текущего года или «все годы»)
        """
        self.kpi_labels = {}  # Словарь для меток со значениями
        self.kpi_title_labels = {}  # Словарь для меток с заголовками
        
        kpi_frame = ttk.LabelFrame(parent, text=TEXT_KPI_TITLE, padding=(8, 6))
        kpi_frame.grid(row=0, column=1, sticky="nsew")

        # Определение структуры KPI-панели (ключ, заголовок, строка, столбец)
        items = [
            ("period", TEXT_KPI_PERIOD, 0, 0),
            ("records", TEXT_KPI_RECORDS, 0, 1),
            ("total", TEXT_KPI_TOTAL, 0, 2),
            ("avg", TEXT_KPI_AVG, 1, 0),
            ("best_month", TEXT_KPI_BEST_MONTH, 1, 1),
            ("best_year", TEXT_KPI_BEST_YEAR, 1, 2),
            ("forecast", "", 0, 3),
        ]

        # Создание ячеек KPI
        for key, title, row, col in items:
            cell = ttk.Frame(kpi_frame)
            cell.grid(row=row, column=col, sticky="nsew", padx=6, pady=4)
            
            # Заголовок метрики
            title_label = ttk.Label(cell, text=title, font=('Segoe UI', 9))
            title_label.pack(anchor="w")
            
            # Значение метрики (по умолчанию "—")
            value_label = ttk.Label(cell, text="—", font=('Segoe UI', 11, 'bold'))
            value_label.pack(anchor="w")
            
            # Сохранение ссылок на метки
            self.kpi_title_labels[key] = title_label
            self.kpi_labels[key] = value_label

        # Настройка растягивания колонок и строк
        for col in range(4):
            kpi_frame.grid_columnconfigure(col, weight=1)
        for row in range(2):
            kpi_frame.grid_rowconfigure(row, weight=1)

    def _create_chart_tabs(self):
        """Создать вкладки с различными графиками"""
        # Вкладка 1: Помесячные данные
        monthly_frame = ttk.Frame(self.notebook)
        self.notebook.add(monthly_frame, text=TAB_MONTHLY_DATA)
        self._create_monthly_chart(monthly_frame)
        
        # Вкладка 2: Сравнение по годам
        yearly_frame = ttk.Frame(self.notebook)
        self.notebook.add(yearly_frame, text=TAB_YEARLY_COMPARISON)
        self._create_yearly_chart(yearly_frame)
        
        # Вкладка 3: Темпы роста
        growth_frame = ttk.Frame(self.notebook)
        self.notebook.add(growth_frame, text=TAB_GROWTH_RATES)
        self._create_growth_chart(growth_frame)
        
        # Вкладка 4: Средние значения
        avg_frame = ttk.Frame(self.notebook)
        self.notebook.add(avg_frame, text=TAB_AVERAGE_VALUES)
        self._create_average_chart(avg_frame)
    
    def _create_monthly_chart(self, parent):
        """
        Создать график помесячных данных.
        
        Отображает доход по месяцам выбранного года или за все время.
        Может показывать раздельно аванс и зарплату или общую сумму.
        """
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=PADX_DEFAULT, pady=PADY_DEFAULT)
        
        # Создание фигуры matplotlib с оптимальным размером
        fig = self._figure_cls(figsize=(8, 4.7), dpi=100)
        ax = fig.add_subplot(111)
        
        # Настройка заголовка и подписей осей
        ax.set_title(CHART_MONTHLY_TITLE, fontsize=14, fontweight='bold')
        ax.set_xlabel(AXIS_X_MONTHS)
        ax.set_ylabel(AXIS_Y_AMOUNT)
        ax.grid(True, alpha=0.3)  # Сетка с прозрачностью
        
        # Уменьшение пустых полей вокруг графика
        fig.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.12)
        
        # Создание холста для отображения графика в Tkinter
        canvas = self._figure_canvas_cls(fig, master=frame)
        canvas.draw()
        
        # Использование grid для контроля размера
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        # Настройка растягивания
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        tooltip = BarChartTooltip(ax, canvas, canvas.get_tk_widget())

        # Сохранение объектов графика для последующего обновления
        self.charts['monthly'] = {
            'fig': fig,
            'ax': ax,
            'canvas': canvas,
            'tooltip': tooltip
        }
    
    def _create_yearly_chart(self, parent):
        """
        Создать график сравнения по годам.
        
        Столбчатая диаграмма, показывающая общий доход по каждому году.
        """
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=PADX_DEFAULT, pady=PADY_DEFAULT)
        
        fig = self._figure_cls(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111)
        
        ax.set_title(CHART_YEARLY_TITLE, fontsize=14, fontweight='bold')
        ax.set_xlabel(AXIS_X_YEARS)
        ax.set_ylabel(AXIS_Y_TOTAL)
        ax.grid(True, alpha=0.3)
        
        # Уменьшение пустых полей
        fig.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.12)

        canvas = self._figure_canvas_cls(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.charts['yearly'] = {
            'fig': fig,
            'ax': ax,
            'canvas': canvas
        }
    
    def _create_growth_chart(self, parent):
        """
        Создать график темпов роста.
        
        Линейный график, показывающий процентное изменение доходов
        относительно предыдущего периода (месяца или года).
        """
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=PADX_DEFAULT, pady=PADY_DEFAULT)
        
        fig = self._figure_cls(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111)
        
        ax.set_title(CHART_GROWTH_TITLE, fontsize=14, fontweight='bold')
        ax.set_xlabel(AXIS_X_PERIODS)
        ax.set_ylabel(AXIS_Y_GROWTH)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)  # Нулевая линия
        
        fig.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.12)

        canvas = self._figure_canvas_cls(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.charts['growth'] = {
            'fig': fig,
            'ax': ax,
            'canvas': canvas
        }
    
    def _create_average_chart(self, parent):
        """
        Создать график средних значений.
        
        Показывает средний доход по каждому месяцу за все годы,
        полезно для выявления сезонных тенденций.
        """
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=PADX_DEFAULT, pady=PADY_DEFAULT)
        
        fig = self._figure_cls(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111)
        
        ax.set_title(CHART_AVERAGE_TITLE, fontsize=14, fontweight='bold')
        ax.set_xlabel(AXIS_X_MONTHS)
        ax.set_ylabel(AXIS_Y_AVERAGE)
        ax.grid(True, alpha=0.3)
        
        fig.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.12)

        canvas = self._figure_canvas_cls(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.charts['average'] = {
            'fig': fig,
            'ax': ax,
            'canvas': canvas
        }
    
    def _refresh_charts(self):
        """Обновить все графики на основе выбранного года"""
        # Получаем выбранный год из combobox
        selected_year = self.get_selected_year()
        
        # Вызываем метод контроллера для загрузки новых данных
        if hasattr(self.controller, 'on_year_selected'):
            self.controller.on_year_selected(selected_year)
    
    def get_selected_year(self):
        """
        Получить выбранный год из combobox.
        
        Returns:
            int или None: Выбранный год или None для "Все годы"
        """
        year_str = self.year_var.get()
        if year_str == TEXT_ALL_YEARS or not year_str:
            return None  # "Все годы" или пустое значение
        try:
            return int(year_str)
        except ValueError:
            return None  # Некорректное значение
    
    def update_years_list(self, years):
        """
        Обновить список лет в combobox.
        
        Args:
            years: Список лет с данными
        """
        # Формируем список: "Все годы" + отсортированные годы
        years_list = [TEXT_ALL_YEARS] + [str(year) for year in years]
        self.year_combobox['values'] = years_list
        
        # Если текущее значение не в списке, выбираем "Все годы"
        if not self.year_var.get() or self.year_var.get() not in years_list:
            self.year_var.set(TEXT_ALL_YEARS)
    
    def update_monthly_chart(self, data):
        """
        Обновить график помесячных данных.
        
        Args:
            data: Данные для графика в формате DTO
        """
        if 'monthly' not in self.charts:
            return
        
        chart = self.charts['monthly']
        ax = chart['ax']
        canvas = chart['canvas']
        tooltip = chart.get('tooltip')
        tooltip_items = []
        if tooltip is not None:
            tooltip.clear()
        
        # Очистка графика перед обновлением
        ax.clear()
        
        # Подготовка данных через presenter
        if data and isinstance(data, dict) and "items" in data:
            model = self.presenter.prepare_monthly_dto(data)
        else:
            model = {"has_data": False}
        
        # Отрисовка графика если есть данные
        if model.get("has_data"):
            labels = model.get("labels", [])
            datasets = model.get("datasets", [])
            is_all_years = bool(model.get("is_all_years"))

            # Цвета по умолчанию для графиков
            default_colors = ["#FF6384", "#36A2EB", "#4BC0C0"]

            if len(labels) > 0:
                x = range(len(labels))

                if is_all_years:
                    # График для всех лет (один набор данных)
                    values = model.get("values", [])
                    color = model.get("color", default_colors[2])
                    bars = ax.bar(x, values, 0.6, color=color, alpha=0.75, label=model.get("label", "Итого"))
                    tooltip_items.extend(zip(bars, model.get("tooltips", [])))

                    # Линия тренда (скользящее среднее)
                    trend = model.get("trend", [])
                    if trend:
                        ax.plot(
                            list(x),
                            trend,
                            color="#2c3e50",
                            linewidth=1.6,
                            alpha=0.7,
                            label=model.get("trend_label", "Тренд (3 мес)")
                        )

                    # Настройка подписей оси X
                    tick_positions = model.get("tick_positions", [])
                    tick_labels = model.get("tick_labels", labels)

                    ax.set_xticks(tick_positions if tick_positions else range(len(labels)))
                    ax.set_xticklabels(tick_labels, rotation=0)
                    ax.legend()
                else:
                    # График для конкретного года (раздельно аванс и зарплата)
                    # 3 серии — как раньше (ширина 0.25); 4-я — доп. выплаты, если были
                    width = 0.75 / len(datasets[:4])
                    for i, dataset in enumerate(datasets[:4]):
                        values = dataset.get("data", [])
                        label = dataset.get("label", "")
                        color = dataset.get("backgroundColor", default_colors[i] if i < len(default_colors) else f"C{i}")
                        bars = ax.bar(
                            [pos + i * width for pos in x],
                            values,
                            width,
                            label=label,
                            color=color,
                            alpha=0.7
                        )
                        tooltip_items.extend(zip(bars, dataset.get("tooltips", [])))
                    ax.set_xticks([pos + width * (len(datasets[:4]) - 1) / 2 for pos in x])
                    ax.set_xticklabels(labels, rotation=0)
                    ax.legend()

                # Настройка осей и заголовка
                ax.set_xlabel("")
                ax.set_ylabel(AXIS_Y_AMOUNT)
                ax.set_title(CHART_MONTHLY_TITLE, fontsize=14, fontweight="bold")
                ax.grid(True, alpha=0.3)
                ax.margins(x=0.01)  # Уменьшение боковых отступов
            else:
                # Нет данных для отображения
                ax.text(0.5, 0.5, TEXT_NO_DATA, 
                       horizontalalignment="center", verticalalignment="center",
                       transform=ax.transAxes, fontsize=12)
                ax.set_title(CHART_MONTHLY_TITLE, fontsize=14, fontweight="bold")
        else:
            # Нет данных
            ax.text(0.5, 0.5, TEXT_NO_DATA, 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=12)
            ax.set_title(CHART_MONTHLY_TITLE, fontsize=14, fontweight='bold')
        
        if tooltip is not None:
            tooltip.set_items(tooltip_items)

        # Перерисовка холста
        canvas.draw()
    
    def update_yearly_chart(self, data):
        """
        Обновить график сравнения по годам.
        
        Args:
            data: Данные для столбчатой диаграммы по годам
        """
        if 'yearly' not in self.charts:
            return
        
        chart = self.charts['yearly']
        ax = chart['ax']
        canvas = chart['canvas']
        
        ax.clear()
        
        if data and isinstance(data, dict) and "items" in data:
            model = self.presenter.prepare_yearly_dto(data)
        else:
            model = {"has_data": False}
            
        if model.get("has_data"):
            labels = model.get("labels", [])
            values = model.get("values", [])
            color = model.get("color", "#4A90E2")
            
            if len(labels) > 0:
                x = range(len(labels))
                bars = ax.bar(x, values, color=color, alpha=0.7)
                
                # Добавление значений над столбцами
                for bar in bars:
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.,
                        height,
                        f'{height:,.0f}'.replace(',', ' '),  # без копеек, тысячи — пробелом
                        ha='center',
                        va='bottom',
                        fontsize=9
                    )
                
                ax.set_xlabel("")
                ax.set_ylabel(AXIS_Y_TOTAL)
                ax.set_title(CHART_YEARLY_TITLE, fontsize=14, fontweight='bold')
                ax.set_xticks(x)
                ax.set_xticklabels(labels)
                ax.grid(True, alpha=0.3)
            else:
                ax.text(0.5, 0.5, TEXT_NO_DATA, 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=12)
                ax.set_title(CHART_YEARLY_TITLE, fontsize=14, fontweight='bold')
        else:
            ax.text(0.5, 0.5, TEXT_NO_DATA, 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=12)
            ax.set_title(CHART_YEARLY_TITLE, fontsize=14, fontweight='bold')
        
        canvas.draw()
    
    def update_growth_chart(self, data):
        """
        Обновить график темпов роста.
        
        Args:
            data: Данные для линейного графика роста
        """
        if 'growth' not in self.charts:
            return
        
        chart = self.charts['growth']
        ax = chart['ax']
        canvas = chart['canvas']
        
        ax.clear()
        
        if data and isinstance(data, dict) and "items" in data:
            model = self.presenter.prepare_growth_dto(data)
        else:
            model = {"has_data": False}
            
        if model.get("has_data"):
            labels = model.get("labels", [])
            values = model.get("values", [])
            color = model.get("color", "#FF8C42")
            fill_color = model.get("fill_color", "#FF8C42")
            
            if len(labels) > 0:
                x = range(len(labels))
                ax.plot(x, values, marker='s', color=color, linewidth=2, markersize=6)
                
                # Заливка под линией
                ax.fill_between(x, values, alpha=0.2, color=fill_color)
                
                # Добавление значений над точками
                for i, (xi, yi) in enumerate(zip(x, values)):
                    ax.text(xi, yi, f'{yi:.1f}%', ha='center', va='bottom', fontsize=9)
                
                ax.set_xlabel("")
                ax.set_ylabel(AXIS_Y_GROWTH)
                ax.set_title(CHART_GROWTH_TITLE, fontsize=14, fontweight='bold')
                ax.set_xticks(x)
                ax.set_xticklabels(labels, rotation=0)
                ax.grid(True, alpha=0.3)
                ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

                # Добавление примечания если есть
                note = model.get("note")
                if note:
                    ax.text(
                        0.99,
                        -0.12,
                        note,
                        transform=ax.transAxes,
                        ha='right',
                        va='top',
                        fontsize=9
                    )
            else:
                ax.text(0.5, 0.5, TEXT_NO_DATA, 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=12)
                ax.set_title(CHART_GROWTH_TITLE, fontsize=14, fontweight='bold')
        else:
            ax.text(0.5, 0.5, TEXT_NO_DATA, 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=12)
            ax.set_title(CHART_GROWTH_TITLE, fontsize=14, fontweight='bold')
        
        canvas.draw()
    
    def update_average_chart(self, data):
        """
        Обновить график средних значений.
        
        Args:
            data: Данные для графика средних по месяцам
        """
        if 'average' not in self.charts:
            return
        
        chart = self.charts['average']
        ax = chart['ax']
        canvas = chart['canvas']
        
        ax.clear()
        
        if data and isinstance(data, dict) and "items" in data:
            model = self.presenter.prepare_average_dto(data)
        else:
            model = {"has_data": False}
            
        if model.get("has_data"):
            labels = model.get("labels", [])
            datasets = model.get("datasets", [])
            
            # Цвета по умолчанию
            default_colors = ['#FF6384', '#36A2EB', '#4BC0C0']

            if len(labels) > 0:
                # Отрисовка нескольких линий (например, по годам)
                for i, dataset in enumerate(datasets):
                    values = dataset['data']
                    label = dataset['label']
                    color = dataset.get('borderColor', default_colors[i] if i < len(default_colors) else f'C{i}')
                    
                    x = range(len(labels))
                    ax.plot(x, values, marker='s', label=label, color=color, linewidth=2, markersize=6)
                
                ax.set_xlabel("")
                ax.set_ylabel(AXIS_Y_AVERAGE)
                ax.set_title(CHART_AVERAGE_TITLE, fontsize=14, fontweight='bold')
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels, rotation=0)
                ax.legend()
                ax.grid(True, alpha=0.3)
            else:
                ax.text(0.5, 0.5, TEXT_NO_DATA, 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=12)
                ax.set_title(CHART_AVERAGE_TITLE, fontsize=14, fontweight='bold')
        else:
            ax.text(0.5, 0.5, TEXT_NO_DATA, 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=12)
            ax.set_title(CHART_AVERAGE_TITLE, fontsize=14, fontweight='bold')
        
        canvas.draw()

    def update_kpi(
        self,
        summary,
        best_month=None,
        best_year=None,
        selected_year=None,
        show_best_year_always=True,
        currency="руб.",
        forecast=None,
    ):
        """
        Обновить панель быстрых итогов (KPI).
        
        Args:
            summary: Сводная статистика
            best_month: Данные о лучшем месяце
            best_year: Данные о лучшем годе
            selected_year: Выбранный год (или None для всех)
            show_best_year_always: Показывать ли лучший год всегда
            forecast: Прогноз итога текущего года или None
        """
        if not hasattr(self, "kpi_labels"):
            return

        # Подготовка данных через presenter
        model = self.presenter.prepare_kpi(
            summary,
            best_month,
            best_year,
            selected_year,
            show_best_year_always,
            currency,
            forecast,
        )

        # Обновление значений KPI
        self.kpi_labels["total"].config(text=model["total"])
        self.kpi_labels["avg"].config(text=model["avg"])
        self.kpi_title_labels["avg"].config(text=model["avg_title"])
        self.kpi_labels["best_month"].config(text=model["best_month"])

        # Условное отображение лучшего года
        if model["show_best_year"]:
            if "best_year" in self.kpi_title_labels:
                self.kpi_title_labels["best_year"].config(text=TEXT_KPI_BEST_YEAR)
            self.kpi_labels["best_year"].config(text=model["best_year"])
        else:
            if "best_year" in self.kpi_title_labels:
                self.kpi_title_labels["best_year"].config(text="")
            self.kpi_labels["best_year"].config(text="")

        # Остальные KPI
        self.kpi_labels["records"].config(text=model["records"])
        self.kpi_labels["period"].config(text=model["period"])

        # Прогноз — только когда он есть (текущий год), иначе ячейка пустая
        self.kpi_title_labels["forecast"].config(text=model["forecast_title"])
        self.kpi_labels["forecast"].config(text=model["forecast"])

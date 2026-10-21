import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from typing import Dict, Any
from desktop.views.base_view import BaseView
from desktop.views.constants import (
    PADX_DEFAULT, PADY_DEFAULT,
    TEXT_GENERAL_SETTINGS, TEXT_MAIN_TAB_SETTINGS, TEXT_ANALYTICS_TAB_SETTINGS,
    TEXT_CURRENCY,
    TEXT_HISTORY_LAYOUT, TEXT_HISTORY_LAYOUT_STANDARD, TEXT_HISTORY_LAYOUT_QUARTERLY,
    TEXT_MAIN_STATS_LAYOUT, TEXT_MAIN_STATS_LAYOUT_ROW, TEXT_MAIN_STATS_LAYOUT_COLUMN,
    TEXT_FONT_SIZE_SETTINGS,
    TEXT_MONTH_TITLE_FONT_SIZE, TEXT_MONTH_TOTAL_FONT_SIZE, TEXT_MONTH_DATA_FONT_SIZE,
    TEXT_COLOR_SETTINGS,
    TEXT_ADVANCE_COLOR, TEXT_SALARY_COLOR, TEXT_TOTAL_COLOR, TEXT_SHOW_BEST_YEAR_ALWAYS,
    TEXT_BACKUP_SETTINGS, TEXT_AUTO_BACKUP, TEXT_BACKUP_RETENTION,
    TEXT_EXPORT_SETTINGS, TEXT_DEFAULT_EXPORT_FORMAT,
    TEXT_SAVE_SETTINGS, TEXT_RESET_SETTINGS,
    DEFAULT_CURRENCY, DEFAULT_BACKUP_DAYS, DEFAULT_EXPORT_FORMAT,
    DEFAULT_ADVANCE_COLOR, DEFAULT_SALARY_COLOR, DEFAULT_TOTAL_COLOR, DEFAULT_SHOW_BEST_YEAR_ALWAYS,
    DEFAULT_HISTORY_LAYOUT_MODE, DEFAULT_MAIN_STATS_LAYOUT_MODE,
    DEFAULT_MONTH_TITLE_FONT_SIZE, DEFAULT_MONTH_TOTAL_FONT_SIZE, DEFAULT_MONTH_DATA_FONT_SIZE,
    CONFIRM_TITLE, CONFIRM_RESET_SETTINGS, SETTINGS_ENTRY_WIDTH, SETTINGS_SPINBOX_WIDTH, SETTINGS_COMBOBOX_WIDTH
)


class SettingsView(BaseView):
    """Вкладка настроек приложения."""
    
    def __init__(self, parent, controller):
        self.settings_vars = {}
        super().__init__(parent, controller)
    
    def _create_widgets(self):
        """Создать основные виджеты без прокрутки."""
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        self._create_content(self.main_container)
    
    def _create_content(self, parent):
        """Создать и разложить секции настроек."""
        self.top_frame = ttk.Frame(parent)
        self.top_frame.pack(fill=tk.BOTH, expand=True)
        
        self.bottom_frame = ttk.Frame(parent)
        self.bottom_frame.pack(fill=tk.X, pady=(8, 0))
        
        self._create_general_and_export_settings(self.top_frame)
        self._create_main_tab_settings(self.top_frame)
        self._create_analytics_tab_settings(self.top_frame)
        
        self._create_backup_settings(self.top_frame)
        self._create_button_panel(self.bottom_frame)
    
    def _create_general_and_export_settings(self, parent):
        """Верхний ряд: общие настройки и настройки экспорта."""
        top_row = ttk.Frame(parent)
        top_row.pack(fill=tk.X, padx=0, pady=(0, PADY_DEFAULT))
        top_row.columnconfigure(0, weight=1, uniform="settings_top_halves")
        top_row.columnconfigure(1, weight=1, uniform="settings_top_halves")

        self._create_general_settings(top_row)
        self._create_export_settings(top_row)

    def _create_general_settings(self, parent):
        """Раздел общих настроек."""
        frame = ttk.LabelFrame(parent, text=TEXT_GENERAL_SETTINGS, padding=PADX_DEFAULT)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # Валюта (формат даты убран: даты везде ДД.ММ.ГГГГ, настройка ни на что не влияла)
        currency_frame = ttk.Frame(frame)
        currency_frame.pack(fill=tk.X, pady=(6, 4))
        ttk.Label(currency_frame, text=TEXT_CURRENCY).pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
        self.settings_vars['currency'] = tk.StringVar(value=DEFAULT_CURRENCY)
        currency_entry = ttk.Entry(
            currency_frame, 
            textvariable=self.settings_vars['currency'], 
            width=SETTINGS_ENTRY_WIDTH
        )
        currency_entry.pack(side=tk.LEFT)

    def _create_main_tab_settings(self, parent):
        """Раздел настроек отображения вкладки Главная."""
        frame = ttk.LabelFrame(parent, text=TEXT_MAIN_TAB_SETTINGS, padding=PADX_DEFAULT)
        frame.pack(fill=tk.X, padx=0, pady=(0, PADY_DEFAULT))

        # Верхний ряд: вид истории + вид блока статистики
        top_row = ttk.Frame(frame)
        top_row.pack(fill=tk.X, pady=(6, 6))
        top_row.columnconfigure(0, weight=1, uniform="main_top_halves")
        top_row.columnconfigure(1, weight=1, uniform="main_top_halves")

        history_layout_frame = ttk.LabelFrame(top_row, text=TEXT_HISTORY_LAYOUT, padding=8)
        history_layout_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.settings_vars['history_layout_mode'] = tk.StringVar(value=DEFAULT_HISTORY_LAYOUT_MODE)

        ttk.Radiobutton(
            history_layout_frame,
            text=TEXT_HISTORY_LAYOUT_STANDARD,
            variable=self.settings_vars['history_layout_mode'],
            value='standard'
        ).pack(anchor=tk.W, pady=(4, 0))

        ttk.Radiobutton(
            history_layout_frame,
            text=TEXT_HISTORY_LAYOUT_QUARTERLY,
            variable=self.settings_vars['history_layout_mode'],
            value='quarterly'
        ).pack(anchor=tk.W, pady=(0, 2))

        stats_layout_frame = ttk.LabelFrame(top_row, text=TEXT_MAIN_STATS_LAYOUT, padding=8)
        stats_layout_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        self.settings_vars['main_stats_layout_mode'] = tk.StringVar(value=DEFAULT_MAIN_STATS_LAYOUT_MODE)

        ttk.Radiobutton(
            stats_layout_frame,
            text=TEXT_MAIN_STATS_LAYOUT_ROW,
            variable=self.settings_vars['main_stats_layout_mode'],
            value='row'
        ).pack(anchor=tk.W, pady=(4, 0))

        ttk.Radiobutton(
            stats_layout_frame,
            text=TEXT_MAIN_STATS_LAYOUT_COLUMN,
            variable=self.settings_vars['main_stats_layout_mode'],
            value='column'
        ).pack(anchor=tk.W, pady=(0, 2))

        # Нижний ряд: размеры шрифта + настройки цвета
        bottom_row = ttk.Frame(frame)
        bottom_row.pack(fill=tk.X, pady=(0, 6))
        bottom_row.columnconfigure(0, weight=1, uniform="main_bottom_halves")
        bottom_row.columnconfigure(1, weight=1, uniform="main_bottom_halves")

        colors_block = ttk.LabelFrame(bottom_row, text=TEXT_COLOR_SETTINGS, padding=8)
        colors_block.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        color_grid = ttk.Frame(colors_block)
        color_grid.pack(fill=tk.X, pady=(0, 6))
        color_grid.columnconfigure(0, weight=0)
        color_grid.columnconfigure(1, weight=0)
        color_grid.columnconfigure(2, weight=0)
        color_grid.columnconfigure(3, weight=0)

        ttk.Label(color_grid, text=TEXT_ADVANCE_COLOR).grid(row=0, column=0, sticky="w", padx=(0, PADX_DEFAULT), pady=(0, 6))
        self.settings_vars['advance_color'] = tk.StringVar(value=DEFAULT_ADVANCE_COLOR)
        advance_entry = ttk.Entry(
            color_grid,
            textvariable=self.settings_vars['advance_color'],
            width=10
        )
        advance_entry.grid(row=0, column=1, sticky="w", padx=(0, PADX_DEFAULT), pady=(0, 6))

        self._advance_color_preview = tk.Label(color_grid, text=" ", width=2, bg=DEFAULT_ADVANCE_COLOR)
        self._advance_color_preview.grid(row=0, column=2, sticky="w", padx=(0, PADX_DEFAULT), pady=(0, 6))

        ttk.Button(
            color_grid,
            text="Выбрать",
            command=lambda: self._choose_color('advance_color', self._advance_color_preview)
        ).grid(row=0, column=3, sticky="w", pady=(0, 6))

        ttk.Label(color_grid, text=TEXT_SALARY_COLOR).grid(row=1, column=0, sticky="w", padx=(0, PADX_DEFAULT), pady=(0, 6))
        self.settings_vars['salary_color'] = tk.StringVar(value=DEFAULT_SALARY_COLOR)
        salary_entry = ttk.Entry(
            color_grid,
            textvariable=self.settings_vars['salary_color'],
            width=10
        )
        salary_entry.grid(row=1, column=1, sticky="w", padx=(0, PADX_DEFAULT), pady=(0, 6))

        self._salary_color_preview = tk.Label(color_grid, text=" ", width=2, bg=DEFAULT_SALARY_COLOR)
        self._salary_color_preview.grid(row=1, column=2, sticky="w", padx=(0, PADX_DEFAULT), pady=(0, 6))

        ttk.Button(
            color_grid,
            text="Выбрать",
            command=lambda: self._choose_color('salary_color', self._salary_color_preview)
        ).grid(row=1, column=3, sticky="w", pady=(0, 6))

        ttk.Label(color_grid, text=TEXT_TOTAL_COLOR).grid(row=2, column=0, sticky="w", padx=(0, PADX_DEFAULT))
        self.settings_vars['total_color'] = tk.StringVar(value=DEFAULT_TOTAL_COLOR)
        total_entry = ttk.Entry(
            color_grid,
            textvariable=self.settings_vars['total_color'],
            width=10
        )
        total_entry.grid(row=2, column=1, sticky="w", padx=(0, PADX_DEFAULT))

        self._total_color_preview = tk.Label(color_grid, text=" ", width=2, bg=DEFAULT_TOTAL_COLOR)
        self._total_color_preview.grid(row=2, column=2, sticky="w", padx=(0, PADX_DEFAULT))

        ttk.Button(
            color_grid,
            text="Выбрать",
            command=lambda: self._choose_color('total_color', self._total_color_preview)
        ).grid(row=2, column=3, sticky="w")

        font_block = ttk.LabelFrame(bottom_row, text=TEXT_FONT_SIZE_SETTINGS, padding=8)
        font_block.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        font_grid = ttk.Frame(font_block)
        font_grid.pack(fill=tk.X, pady=(0, 2))
        font_grid.columnconfigure(0, weight=0)
        font_grid.columnconfigure(1, weight=0)

        ttk.Label(font_grid, text=TEXT_MONTH_TITLE_FONT_SIZE).grid(row=0, column=0, sticky="w", padx=(0, PADX_DEFAULT), pady=(0, 6))
        self.settings_vars['month_title_font_size'] = tk.IntVar(value=DEFAULT_MONTH_TITLE_FONT_SIZE)
        month_title_font_spin = ttk.Spinbox(
            font_grid,
            from_=7,
            to=18,
            textvariable=self.settings_vars['month_title_font_size'],
            width=SETTINGS_SPINBOX_WIDTH
        )
        month_title_font_spin.grid(row=0, column=1, sticky="w", pady=(0, 6))

        ttk.Label(font_grid, text=TEXT_MONTH_TOTAL_FONT_SIZE).grid(row=1, column=0, sticky="w", padx=(0, PADX_DEFAULT))
        self.settings_vars['month_total_font_size'] = tk.IntVar(value=DEFAULT_MONTH_TOTAL_FONT_SIZE)
        month_total_font_spin = ttk.Spinbox(
            font_grid,
            from_=7,
            to=18,
            textvariable=self.settings_vars['month_total_font_size'],
            width=SETTINGS_SPINBOX_WIDTH
        )
        month_total_font_spin.grid(row=1, column=1, sticky="w")

        ttk.Label(font_grid, text=TEXT_MONTH_DATA_FONT_SIZE).grid(row=2, column=0, sticky="w", padx=(0, PADX_DEFAULT), pady=(6, 0))
        self.settings_vars['month_data_font_size'] = tk.IntVar(value=DEFAULT_MONTH_DATA_FONT_SIZE)
        month_data_font_spin = ttk.Spinbox(
            font_grid,
            from_=7,
            to=18,
            textvariable=self.settings_vars['month_data_font_size'],
            width=SETTINGS_SPINBOX_WIDTH
        )
        month_data_font_spin.grid(row=2, column=1, sticky="w", pady=(6, 0))

    def _create_analytics_tab_settings(self, parent):
        """Раздел настроек отображения вкладки Аналитика."""
        frame = ttk.LabelFrame(parent, text=TEXT_ANALYTICS_TAB_SETTINGS, padding=PADX_DEFAULT)
        frame.pack(fill=tk.X, padx=0, pady=(0, PADY_DEFAULT))

        kpi_frame = ttk.Frame(frame)
        kpi_frame.pack(fill=tk.X, pady=(6, 6))

        self.settings_vars['show_best_year_always'] = tk.BooleanVar(value=DEFAULT_SHOW_BEST_YEAR_ALWAYS)
        ttk.Checkbutton(
            kpi_frame,
            text=TEXT_SHOW_BEST_YEAR_ALWAYS,
            variable=self.settings_vars['show_best_year_always']
        ).pack(anchor=tk.W)
    
    def _create_backup_settings(self, parent):
        """Раздел настроек резервного копирования."""
        frame = ttk.LabelFrame(parent, text=TEXT_BACKUP_SETTINGS, padding=PADX_DEFAULT)
        frame.pack(fill=tk.X, padx=0, pady=(0, PADY_DEFAULT))
        
        auto_frame = ttk.Frame(frame)
        auto_frame.pack(fill=tk.X, pady=(PADY_DEFAULT, PADY_DEFAULT))
        
        self.settings_vars['backup_auto'] = tk.BooleanVar(value=True)
        auto_check = ttk.Checkbutton(
            auto_frame,
            text=TEXT_AUTO_BACKUP,
            variable=self.settings_vars['backup_auto']
        )
        auto_check.pack(anchor=tk.W)
        
        retention_frame = ttk.Frame(frame)
        retention_frame.pack(fill=tk.X, pady=(0, PADY_DEFAULT))
        
        ttk.Label(retention_frame, text=TEXT_BACKUP_RETENTION).pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
        self.settings_vars['backup_days'] = tk.IntVar(value=DEFAULT_BACKUP_DAYS)
        retention_spin = ttk.Spinbox(
            retention_frame,
            from_=1,
            to=365,
            textvariable=self.settings_vars['backup_days'],
            width=SETTINGS_SPINBOX_WIDTH
        )
        retention_spin.pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
    
    def _create_export_settings(self, parent):
        """Раздел настроек экспорта."""
        frame = ttk.LabelFrame(parent, text=TEXT_EXPORT_SETTINGS, padding=PADX_DEFAULT)
        frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        
        format_frame = ttk.Frame(frame)
        format_frame.pack(fill=tk.X, pady=(PADY_DEFAULT, PADY_DEFAULT))
        
        ttk.Label(format_frame, text=TEXT_DEFAULT_EXPORT_FORMAT).pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
        
        self.settings_vars['export_format'] = tk.StringVar(value=DEFAULT_EXPORT_FORMAT)
        format_combobox = ttk.Combobox(
            format_frame,
            textvariable=self.settings_vars['export_format'],
            values=["csv", "json", "excel"],
            state="readonly",
            width=SETTINGS_COMBOBOX_WIDTH
        )
        format_combobox.pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
    
    def _create_button_panel(self, parent):
        """Панель кнопок управления."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=6)

        left_spacer = ttk.Frame(frame)
        left_spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)

        save_button = ttk.Button(
            frame,
            text=TEXT_SAVE_SETTINGS,
            command=self._save_settings,
            style="Primary.TButton"
        )
        save_button.pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))

        reset_button = ttk.Button(
            frame,
            text=TEXT_RESET_SETTINGS,
            command=self._reset_settings
        )
        reset_button.pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))

        right_spacer = ttk.Frame(frame)
        right_spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def update_settings(self, settings: Dict[str, Any]):
        """Обновить значения в UI по данным настроек."""
        for key, value in settings.items():
            if key in self.settings_vars:
                var = self.settings_vars[key]
                
                if isinstance(var, tk.BooleanVar):
                    var.set(str(value).lower() in ('true', '1', 'yes', 'y'))
                elif isinstance(var, tk.IntVar):
                    try:
                        var.set(int(value))
                    except (ValueError, TypeError):
                        var.set(0)
                else:
                    var.set(str(value))

        if 'advance_color' in self.settings_vars:
            self._advance_color_preview.config(bg=self.settings_vars['advance_color'].get())
        if 'salary_color' in self.settings_vars:
            self._salary_color_preview.config(bg=self.settings_vars['salary_color'].get())
        if 'total_color' in self.settings_vars:
            self._total_color_preview.config(bg=self.settings_vars['total_color'].get())
    
    def _save_settings(self):
        """Сохранить настройки."""
        settings = {}
        for key, var in self.settings_vars.items():
            settings[key] = var.get()
        
        self.controller.save_settings(settings)
    
    def _reset_settings(self):
        """Сбросить настройки к значениям по умолчанию."""
        if messagebox.askyesno(CONFIRM_TITLE, CONFIRM_RESET_SETTINGS):
            default_settings = {
                'currency': DEFAULT_CURRENCY,
                'backup_auto': True,
                'backup_days': DEFAULT_BACKUP_DAYS,
                'export_format': DEFAULT_EXPORT_FORMAT,
                'advance_color': DEFAULT_ADVANCE_COLOR,
                'salary_color': DEFAULT_SALARY_COLOR,
                'total_color': DEFAULT_TOTAL_COLOR,
                'show_best_year_always': DEFAULT_SHOW_BEST_YEAR_ALWAYS,
                'history_layout_mode': DEFAULT_HISTORY_LAYOUT_MODE,
                'main_stats_layout_mode': DEFAULT_MAIN_STATS_LAYOUT_MODE,
                'month_title_font_size': DEFAULT_MONTH_TITLE_FONT_SIZE,
                'month_total_font_size': DEFAULT_MONTH_TOTAL_FONT_SIZE,
                'month_data_font_size': DEFAULT_MONTH_DATA_FONT_SIZE,
            }
            
            for key, value in default_settings.items():
                if key in self.settings_vars:
                    var = self.settings_vars[key]
                    if isinstance(var, tk.BooleanVar):
                        var.set(value)
                    elif isinstance(var, tk.IntVar):
                        var.set(value)
                    else:
                        var.set(str(value))

            self._advance_color_preview.config(bg=self.settings_vars['advance_color'].get())
            self._salary_color_preview.config(bg=self.settings_vars['salary_color'].get())
            self._total_color_preview.config(bg=self.settings_vars['total_color'].get())

    def _choose_color(self, key: str, preview_label: tk.Label):
        """Открыть диалог выбора цвета и обновить предпросмотр."""
        initial = self.settings_vars.get(key).get() if key in self.settings_vars else None
        color = colorchooser.askcolor(color=initial)[1]
        if color:
            self.settings_vars[key].set(color)
            preview_label.config(bg=color)


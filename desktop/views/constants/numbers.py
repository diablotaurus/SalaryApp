"""
Числовые константы и размеры для представлений приложения учета зарплаты.
"""

# --- Размеры и отступы ---
PADX_DEFAULT = 10
PADY_DEFAULT = 10
ENTRY_WIDTH = 20
COMBOBOX_WIDTH = 15
SPINBOX_WIDTH = 5

# Единая ширина кнопок действий в диалоговых окнах (для единообразия)
BUTTON_DIALOG_WIDTH = 16

# Ширина кнопок на карточках истории (вкладка «Главная»)
CARD_BUTTON_WIDTH = 16

# Шрифты карточек истории (вкладка «Главная»)
FONT_YEAR_TITLE = ('Segoe UI', 14, 'bold')      # Заголовок года в карточке
FONT_YEAR_ARROW = ('Segoe UI Symbol', 12)       # Стрелка ▶/▼ сворачивания года
FONT_CARD_STATS = ('Segoe UI', 10)              # Строки статистики года
FONT_CARD_SECTION = ('Segoe UI', 11, 'bold')    # Подзаголовок «Помесячная разбивка»
FONT_NO_DATA = ('Segoe UI', 12)                 # Сообщение «Нет данных» (вся вкладка)
FONT_MONTH_NO_DATA = ('Segoe UI', 9, 'italic')  # «Нет данных» в ячейке месяца

# Ширины полей для настроек
SETTINGS_ENTRY_WIDTH = 12       # Ширина полей ввода в настройках (валюта, формат даты)
SETTINGS_SPINBOX_WIDTH = 5      # Ширина Spinbox в настройках (дни хранения)
SETTINGS_COMBOBOX_WIDTH = 10    # Ширина Combobox в настройках (формат экспорта)

# --- Размеры окон ---
# Диалоги «Ввод зарплаты» и «Экспорт» подгоняются под содержимое автоматически
# (фиксированные размеры убраны).
# Константы для главного окна
WINDOW_MAIN_MIN_WIDTH = 1360
WINDOW_MAIN_MIN_HEIGHT = 900
WINDOW_MAIN_DEFAULT_WIDTH = 1360
WINDOW_MAIN_DEFAULT_HEIGHT = 960
# Добавьте другие размеры окон по мере необходимости

# --- Параметры текста ---
TEXT_WRAPLENGTH_EXPORT_INFO = 380

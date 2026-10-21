"""
Текстовые константы для представлений приложения учета зарплаты.
"""

# --- Общие тексты для кнопок и действий ---
TEXT_ADD_DATA = "Добавить данные"
TEXT_REFRESH = "Обновить"
TEXT_SAVE = "Сохранить"
TEXT_CANCEL = "Отмена"
TEXT_CLOSE = "Закрыть"
TEXT_CLEAR = "Очистить"
TEXT_EDIT = "Редактировать"
TEXT_DELETE = "Удалить"
TEXT_EXPORT = "Экспорт"
TEXT_IMPORT = "Импорт"
TEXT_BACKUP = "Резервные копии"

# Служебная метка автокопии при закрытии и её текст в списке копий
BACKUP_COMMENT_AUTO_ON_CLOSE = "auto_on_close"
BACKUP_COMMENT_LABELS = {BACKUP_COMMENT_AUTO_ON_CLOSE: "Автокопия при закрытии"}

# --- Удаление года ---
TEXT_DELETE_YEAR = "Удалить год"
CONFIRM_DELETE_YEAR = "Вы уверены, что хотите удалить все данные за {year} год?\nЭто действие нельзя отменить."

# --- Тексты для главного окна ---
TEXT_ACTIONS = "Действия"
TEXT_HISTORY_TITLE = "История заработной платы"
TEXT_MONTHS_SECTION = "Помесячная разбивка:"
# Стрелки сворачивания карточки года (клик по заголовку года).
# Рисуются шрифтом FONT_YEAR_ARROW: в нём ▶ и ▼ одного размера.
ARROW_YEAR_EXPANDED = "▼"
ARROW_YEAR_COLLAPSED = "▶"
TEXT_STATISTICS_TITLE = "Общая статистика"

# Тексты кнопок главного окна
TEXT_REFRESH_HISTORY = "Обновить историю"
TEXT_EXPORT_HISTORY = "Экспорт истории"

# Заголовки колонок таблицы
COLUMN_YEAR = "Год"
COLUMN_MONTH = "Месяц"
COLUMN_ADVANCE = "Аванс"
COLUMN_SALARY = "Зарплата"
COLUMN_TOTAL = "Итого"

# Статистические метки
TEXT_TOTAL_RECORDS = "Всего записей:"
TEXT_TOTAL_ADVANCE = "Общая сумма авансов:"
TEXT_TOTAL_SALARY = "Общая сумма зарплат:"
TEXT_TOTAL_AMOUNT = "Общая сумма:"
TEXT_AVG_ADVANCE = "Среднемесячный аванс:"
TEXT_AVG_SALARY = "Среднемесячная зарплата:"
TEXT_AVG_TOTAL = "Среднемесячный итого:"

# Контекстное меню
MENU_DELETE_RECORD = "Удалить запись"
MENU_REFRESH = "Обновить"

# --- Тексты для диалога зарплаты ---
DIALOG_SALARY_TITLE = "Ввод данных по зарплате"
TEXT_SELECT_YEAR = "Выберите год:"
TEXT_SELECT_MONTH = "Выберите месяц:"
TEXT_ADVANCE = "Аванс:"
TEXT_SALARY = "Зарплата:"
TEXT_RUBLES = "руб."
TEXT_ADVANCE_DATE = "Дата аванса:"
TEXT_SALARY_DATE = "Дата зарплаты:"
TEXT_DATE_HINT = "Формат даты: ДД.ММ.ГГГГ (можно оставить пустым)"

# Сообщения об ошибках
ERROR_NO_YEAR_MONTH = "Пожалуйста, выберите год и месяц"
ERROR_NEGATIVE_AMOUNTS = "Суммы не могут быть отрицательными"
ERROR_INVALID_FORMAT = "Некорректный формат суммы: {error}"
ERROR_SAVE_FAILED = "Не удалось сохранить данные: {error}"
ERROR_UNEXPECTED = (
    "Произошла непредвиденная ошибка:\n{error}\n\n"
    "Подробности записаны в журнал:\n{log_file}"
)

# Сообщения об успехе
SUCCESS_TITLE = "Успех"
SUCCESS_SAVE_DATA = "Данные о заработной плате успешно сохранены в базу.\nХотите продолжить ввод данных за следующий период?"
SUCCESS_CLEAR_DATA = "Операция очистки завершена.\n{message}"

# --- Тексты для вкладки отчетов ---
TEXT_CHART_SETTINGS = "Настройки графиков"
TEXT_REFRESH_CHARTS = "Обновить графики"
TEXT_ALL_YEARS = "Все годы"
TEXT_YEAR = "Год:"

# Быстрые итоги (аналитика)
TEXT_KPI_TITLE = "Быстрые итоги"
TEXT_KPI_TOTAL = "Общая сумма"
TEXT_KPI_AVG = "Среднемесячно"
TEXT_KPI_BEST_MONTH = "Лучший месяц"
TEXT_KPI_BEST_YEAR = "Лучший год"
TEXT_KPI_RECORDS = "Месяцев с данными"
TEXT_KPI_PERIOD = "Период"
# Названия вкладок
TAB_MONTHLY_DATA = "Помесячные данные"
TAB_YEARLY_COMPARISON = "Сравнение по годам"
TAB_GROWTH_RATES = "Темпы роста"
TAB_AVERAGE_VALUES = "Средние значения"

# Заголовки графиков
CHART_MONTHLY_TITLE = "Зарплата по месяцам"
CHART_YEARLY_TITLE = "Сравнение по годам"
CHART_GROWTH_TITLE = "Темпы роста по годам"
CHART_AVERAGE_TITLE = "Средние значения по месяцам"

# Подписи осей
AXIS_X_MONTHS = "Месяцы"
AXIS_X_YEARS = "Годы"
AXIS_X_PERIODS = "Периоды"
AXIS_Y_AMOUNT = "Сумма, руб."
AXIS_Y_TOTAL = "Общая сумма, руб."
AXIS_Y_GROWTH = "Темп роста, %"
AXIS_Y_AVERAGE = "Средняя сумма, руб."

# Сообщение об отсутствии matplotlib
ERROR_NO_MATPLOTLIB = """Для отображения графиков необходимо установить matplotlib.
Выполните команду: pip install matplotlib"""

TEXT_NO_DATA = "Нет данных для отображения"

# Показывается на вкладке аналитики, пока она строится при первом открытии
TEXT_LOADING_CHARTS = "Загрузка графиков…"

# --- Тексты для вкладки настроек ---
TEXT_GENERAL_SETTINGS = "Общие настройки"
TEXT_MAIN_TAB_SETTINGS = "Вкладка Главная"
TEXT_ANALYTICS_TAB_SETTINGS = "Вкладка Аналитика"
TEXT_CURRENCY = "Валюта:"
TEXT_TELEGRAM_REMINDERS = "Напоминать в Telegram о вводе аванса и зарплаты"
TEXT_HISTORY_LAYOUT = "Вид истории:"
TEXT_HISTORY_LAYOUT_STANDARD = "Стандартный (6х2, карточки года по одной в ряд)"
TEXT_HISTORY_LAYOUT_QUARTERLY = "Поквартальный (3х4, карточки года по две в ряд)"
TEXT_MAIN_STATS_LAYOUT = "Вид блока статистики:"
TEXT_MAIN_STATS_LAYOUT_ROW = "Строкой"
TEXT_MAIN_STATS_LAYOUT_COLUMN = "Столбцом"
TEXT_FONT_SIZE_SETTINGS = "Размер шрифта"
TEXT_MONTH_TITLE_FONT_SIZE = "Названия Месяца:"
TEXT_MONTH_TOTAL_FONT_SIZE = "Строки \"Итого\":"
TEXT_MONTH_DATA_FONT_SIZE = "Данные в карточке месяца:"
TEXT_COLOR_SETTINGS = "Настройки цвета"
TEXT_ADVANCE_COLOR = "Цвет аванса:"
TEXT_SALARY_COLOR = "Цвет зарплаты:"
TEXT_TOTAL_COLOR = "Цвет итого:"
TEXT_SHOW_BEST_YEAR_ALWAYS = "Показывать «Лучший год» всегда"
TEXT_BACKUP_SETTINGS = "Резервное копирование"
TEXT_AUTO_BACKUP = "Автоматическое резервное копирование при закрытии"
TEXT_BACKUP_RETENTION = "Хранить резервные копии (дней):"

TEXT_EXPORT_SETTINGS = "Настройки экспорта"
TEXT_DEFAULT_EXPORT_FORMAT = "Формат экспорта по умолчанию:"

TEXT_SAVE_SETTINGS = "Сохранить настройки"
TEXT_RESET_SETTINGS = "Сбросить к значениям по умолчанию"

# --- Тексты для диалога экспорта ---
DIALOG_EXPORT_TITLE = "Экспорт истории"
TEXT_EXPORT_TO_FILE = "Экспорт данных в файл"
TEXT_SELECT_EXPORT_FORMAT = "Выберите формат экспорта"
TEXT_CSV_FORMAT = "CSV (табличный формат)"
TEXT_JSON_FORMAT = "JSON (структурированный)"
TEXT_EXCEL_FORMAT = "Excel (таблицы Excel)"
TEXT_EXPORT_INFO = "Информация"
TEXT_EXPORT_DETAILS = """Данные будут экспортированы в файл в папке 'exports' рядом с программой.

В экспортируемый файл попадут:
• Все записи о зарплате за все годы
• Сводка по годам и месяцам
• Общая статистика и средние значения

Файл будет сохранен в формате: salary_export_YYYY-MM-DD_HH-MM-SS.[format]"""
TEXT_EXPORT_BUTTON = "Экспортировать"
TEXT_CANCEL_BUTTON = "Отмена"
TEXT_EXPORT_FOLDER = "exports"

# --- Тексты подтверждений ---
CONFIRM_TITLE = "Подтверждение"
CONFIRM_DELETE_RECORD = "Вы уверены, что хотите удалить запись за {month_name} {year} года?"
CONFIRM_CLEAR_MONTH_DATA = "Вы уверены, что хотите очистить данные за {month_name} {year} года?\nЭто действие необратимо."
CONFIRM_RESET_SETTINGS = "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?"

# --- Стандартные сообщения ---
MESSAGE_SUCCESS = "Настройки успешно сохранены"

# --- Значения по умолчанию ---
DEFAULT_CURRENCY = "руб."
DEFAULT_EXPORT_FORMAT = "csv"
DEFAULT_BACKUP_DAYS = 30
DEFAULT_ADVANCE_COLOR = "#0d6efd"
DEFAULT_SALARY_COLOR = "#198754"
DEFAULT_TOTAL_COLOR = "#dc3545"
DEFAULT_SHOW_BEST_YEAR_ALWAYS = True
DEFAULT_TELEGRAM_REMINDERS = True
DEFAULT_HISTORY_LAYOUT_MODE = "standard"
DEFAULT_MAIN_STATS_LAYOUT_MODE = "row"
DEFAULT_MONTH_TITLE_FONT_SIZE = 10
DEFAULT_MONTH_TOTAL_FONT_SIZE = 10
DEFAULT_MONTH_DATA_FONT_SIZE = 9
# --- Диалоговые окна ---
DIALOG_TITLE_ERROR = "Ошибка"
DIALOG_TITLE_CONFIRM = "Подтверждение"
DIALOG_TITLE_SUCCESS = "Успех"

# --- Тексты для вкладки "О программе" ---
ABOUT_FRAME_TITLE = "О программе"
ABOUT_DESCRIPTION = (
    "Учёт личной заработной платы: помесячный учёт аванса и зарплаты, "
    "аналитика и отчёты. Три интерфейса на едином ядре: desktop, веб и Telegram-бот."
)
ABOUT_VERSION_LABEL = "Версия:"
ABOUT_AUTHOR_LABEL = "Автор:"
ABOUT_AUTHOR = "diablotaurus"
ABOUT_LICENSE_LABEL = "Лицензия:"
ABOUT_LICENSE = "Apache-2.0"
ABOUT_GITHUB_LABEL = "Репозиторий:"
ABOUT_GITHUB_URL = "https://github.com/diablotaurus/SalaryApp"

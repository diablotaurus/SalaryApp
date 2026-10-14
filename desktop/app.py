"""
Главный модуль desktop-приложения.

Содержит класс App - главное окно приложения, реализует интерфейс на основе вкладок
и координирует взаимодействие между контроллерами и представлениями.
"""
import logging
import os
import tkinter as tk
from tkinter import messagebox, ttk

from core.config.settings import config
from desktop.controllers.navigation_controller import NavigationController
from desktop.views.constants import (
    DIALOG_TITLE_CONFIRM,
    DIALOG_TITLE_ERROR,
    ERROR_UNEXPECTED,
    WINDOW_MAIN_DEFAULT_HEIGHT,
    WINDOW_MAIN_DEFAULT_WIDTH,
    WINDOW_MAIN_MIN_HEIGHT,
    WINDOW_MAIN_MIN_WIDTH,
)
from desktop.views.main.main_view import MainView
from desktop.views.report.report_view import ReportView
from desktop.views.settings.settings_view import SettingsView

TAB_MAIN_TEXT = "\u0413\u043b\u0430\u0432\u043d\u0430\u044f"
TAB_REPORT_TEXT = "\u0410\u043d\u0430\u043b\u0438\u0442\u0438\u043a\u0430"
TAB_SETTINGS_TEXT = "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438"
CLOSE_CONFIRM_TEXT = (
    "\u0412\u044b \u0443\u0432\u0435\u0440\u0435\u043d\u044b, \u0447\u0442\u043e "
    "\u0445\u043e\u0442\u0438\u0442\u0435 \u0437\u0430\u043a\u0440\u044b\u0442\u044c "
    "\u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435?"
)

logger = logging.getLogger(__name__)


def _desktop_log_file() -> str:
    """\u0424\u0430\u0439\u043b, \u0432 \u043a\u043e\u0442\u043e\u0440\u044b\u0439 \u0441\u0435\u0439\u0447\u0430\u0441 \u043f\u0438\u0448\u0435\u0442 \u0436\u0443\u0440\u043d\u0430\u043b desktop (\u043d\u0430\u0441\u0442\u0440\u0430\u0438\u0432\u0430\u0435\u0442\u0441\u044f \u043f\u0440\u0438 \u0441\u0442\u0430\u0440\u0442\u0435)."""
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            return handler.baseFilename
    return str(config.logging.startup_log_file)


class App(tk.Tk):
    """Главный класс приложения (наследуется от tk.Tk)."""

    def __init__(self):
        """Инициализация главного окна приложения."""
        super().__init__()

        # Настройка главного окна.
        self.title(config.app.display_name_with_version)

        # Устанавливаем начальный размер окна.
        self.geometry(f"{WINDOW_MAIN_DEFAULT_WIDTH}x{WINDOW_MAIN_DEFAULT_HEIGHT}")

        # Устанавливаем минимальный размер окна.
        self.minsize(WINDOW_MAIN_MIN_WIDTH, WINDOW_MAIN_MIN_HEIGHT)

        # Разворачиваем окно на весь экран при запуске.
        self.state("zoomed")

        # Устанавливаем иконку приложения.
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "salary_icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except (OSError, tk.TclError):
            # Если иконку не удалось загрузить, продолжаем без нее.
            pass

        # Создаем контроллер навигации для управления вкладками.
        self.navigation_controller = NavigationController(self)

        # Создаем стили для виджетов ttk.
        self._create_styles()

        # Создаем пользовательский интерфейс.
        self._create_ui()

        # Загружаем начальные данные в главную вкладку.
        self.navigation_controller.show_main_view()

        # Подтверждение перед закрытием главного окна.
        self.protocol("WM_DELETE_WINDOW", self._on_close_requested)

    def _create_styles(self):
        """Создать стили для виджетов ttk."""
        style = ttk.Style()

        # Используем тему 'clam', если она доступна.
        if "clam" in style.theme_names():
            style.theme_use("clam")

        # Настраиваем стили для различных элементов интерфейса.

        # Стиль для заголовков.
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Heading.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("Bold.TLabel", font=("Segoe UI", 10, "bold"))

        # Стили для кнопок разных типов.
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Success.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"))

        # Стиль для таблиц (Treeview).
        style.configure("Treeview", font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _create_ui(self):
        """Создать пользовательский интерфейс с вкладками."""
        # Создаем панель вкладок (Notebook) как основной контейнер.
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Создаем представления для каждой вкладки.
        self.main_view = MainView(self.notebook, self.navigation_controller)
        self.report_view = ReportView(self.notebook, self.navigation_controller)
        self.settings_view = SettingsView(self.notebook, self.navigation_controller)

        # Добавляем вкладки в Notebook.
        self.notebook.add(self.main_view, text=TAB_MAIN_TEXT)
        self.notebook.add(self.report_view, text=TAB_REPORT_TEXT)
        self.notebook.add(self.settings_view, text=TAB_SETTINGS_TEXT)

        # Привязываем обработчик события смены вкладки.
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event):
        """Обработчик смены активной вкладки."""
        # Получаем идентификатор текущей вкладки.
        tab_id = self.notebook.select()
        # Получаем индекс вкладки (0, 1 или 2).
        tab_index = self.notebook.index(tab_id)

        # В зависимости от индекса вкладки обновляем соответствующие данные.
        if tab_index == 0:  # Главная вкладка.
            self.navigation_controller.refresh_history()
        elif tab_index == 1:  # Вкладка аналитики.
            self.navigation_controller.refresh_reports()
        elif tab_index == 2:  # Вкладка настроек.
            self.navigation_controller.refresh_settings()

    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        """
        Необработанная ошибка в обработчике Tk (кнопка, клавиша, диалог).

        По умолчанию Tk печатает её в консоль, которой у pythonw нет, и ошибка
        пропадала бесследно. Теперь она пишется в журнал и показывается пользователю.
        """
        logger.error(
            "Необработанная ошибка в интерфейсе",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        try:
            messagebox.showerror(
                DIALOG_TITLE_ERROR,
                ERROR_UNEXPECTED.format(error=exc_value, log_file=_desktop_log_file()),
            )
        except tk.TclError:
            # Окно уже закрывается — ошибка всё равно записана в журнал
            pass

    def show_message(self, title: str, message: str, message_type: str = "info"):
        """
        Показать диалоговое окно с сообщением.

        Args:
            title: Заголовок окна.
            message: Текст сообщения.
            message_type: Тип сообщения ("info", "warning", "error", "question").

        Returns:
            Для типа "question" возвращает ответ пользователя (True/False),
            для других типов возвращает None.
        """
        if message_type == "info":
            messagebox.showinfo(title, message)
        elif message_type == "warning":
            messagebox.showwarning(title, message)
        elif message_type == "error":
            messagebox.showerror(title, message)
        elif message_type == "question":
            return messagebox.askyesno(title, message)
        return None

    def _on_close_requested(self):
        """Обработчик попытки закрытия главного окна приложения."""
        should_close = messagebox.askyesno(
            DIALOG_TITLE_CONFIRM,
            CLOSE_CONFIRM_TEXT
        )
        if should_close:
            self.navigation_controller.create_auto_backup_on_close()
            self.destroy()

    def run(self):
        """Запустить главный цикл приложения."""
        self.mainloop()

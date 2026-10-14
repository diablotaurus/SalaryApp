"""
Модуль конфигурации приложения.

Обеспечивает централизованное управление настройками приложения с поддержкой окружений
(development/production). Использует паттерн Singleton для глобального доступа к конфигурации.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

def get_environment_info() -> tuple[bool, str]:
    """
    Определяет окружение и читает информацию из маркера.
    
    Returns:
        tuple[bool, str]: (is_production, marker_text)
        
    Логика работы:
        1. Проверяет наличие файла prod.marker в корневой директории проекта
        2. Если файл существует - окружение считается production
        3. Читает содержимое файла как предупреждение для пользователя
    """
    root_dir = Path(__file__).parent.parent.parent
    prod_marker = root_dir / "prod.marker"
    
    if prod_marker.exists():
        try:
            # Читаем текст из маркера для отображения в UI
            marker_text = prod_marker.read_text(encoding='utf-8').strip()
            if not marker_text:
                marker_text = "РЕАЛЬНАЯ БАЗА ДАННЫХ"
            return True, marker_text
        except Exception:
            logger.exception("[CONFIG] Ошибка чтения prod.marker")
            # В случае ошибки возвращаем production с текстом по умолчанию
            return True, "РЕАЛЬНАЯ БАЗА ДАННЫХ"
    # Если маркер отсутствует - окружение development
    return False, ""


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    path: str = None  # Будет определяться динамически
    backup_dir: str = "db/backup"
    backup_retention_days: int = 30  # Дней хранения резервных копий
    
    def __post_init__(self):
        root_dir = Path(__file__).resolve().parent.parent.parent
        """Динамически определяем путь к БД в зависимости от окружения"""
        if self.path is None:
            # Определяем окружение
            is_production, _ = get_environment_info()
            
            if is_production:
                # Production окружение - используем отдельную базу
                # Это предотвращает случайную потерю реальных данных во время разработки
                self.path = "db/prod_salary.db"
                logger.warning("[CONFIG] Окружение: PRODUCTION")
                logger.warning("[CONFIG] Используется база данных: %s", self.path)
                logger.warning("[CONFIG] ВНИМАНИЕ: Работа с реальными данными!")
            else:
                # Development/Test окружение - используем тестовую базу
                self.path = "db/salary.db"
                logger.info("[CONFIG] Окружение: DEVELOPMENT/TESTING")
                logger.info("[CONFIG] Используется база данных: %s", self.path)

        # Создаем директорию для базы данных, если её нет
        db_path = Path(self.path)
        if not db_path.is_absolute():
            db_path = root_dir / db_path
        self.path = str(db_path)
        backup_path = Path(self.backup_dir)
        if not backup_path.is_absolute():
            backup_path = root_dir / backup_path
        self.backup_dir = str(backup_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.mkdir(parents=True, exist_ok=True)


@dataclass
class ExportConfig:
    """Конфигурация экспорта данных"""
    default_format: str = "csv"
    available_formats: list = None
    export_dir: str = "exports"
    
    def __post_init__(self):
        if self.available_formats is None:
            self.available_formats = ["csv", "json", "excel"]
        
        # Создаем директорию для экспорта, если её нет
        export_path = Path(self.export_dir)
        if not export_path.is_absolute():
            export_path = Path(__file__).resolve().parent.parent.parent / export_path
        self.export_dir = str(export_path)
        export_path.mkdir(parents=True, exist_ok=True)


@dataclass
class LoggingConfig:
    """Конфигурация системы логирования"""
    level: str = "INFO"
    format: str = "%(asctime)s %(levelname)s %(message)s"
    app_log_file: str = "logs/app.log"
    startup_log_file: str = "logs/startup.log"
    bot_log_file: str = "logs/bot.log"
    web_log_file: str = "logs/web.log"

    def __post_init__(self):
        """Инициализация путей логирования с учетом корневой директории"""
        root_dir = Path(__file__).parent.parent.parent
        # Разрешаем относительные пути относительно корня проекта
        self.app_log_file = str(self._resolve_path(root_dir, self.app_log_file))
        self.startup_log_file = str(self._resolve_path(root_dir, self.startup_log_file))
        self.bot_log_file = str(self._resolve_path(root_dir, self.bot_log_file))
        self.web_log_file = str(self._resolve_path(root_dir, self.web_log_file))

        # Создаем директории для логов
        Path(self.app_log_file).parent.mkdir(parents=True, exist_ok=True)
        Path(self.startup_log_file).parent.mkdir(parents=True, exist_ok=True)
        Path(self.bot_log_file).parent.mkdir(parents=True, exist_ok=True)
        Path(self.web_log_file).parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _resolve_path(root_dir: Path, value: str) -> Path:
        """Разрешение пути: если путь абсолютный - используется как есть, иначе - относительно корня"""
        path = Path(value)
        if path.is_absolute():
            return path
        return root_dir / path


@dataclass
class AppConfig:
    """Основная конфигурация приложения"""
    app_name: str = "Salary Tracker"
    display_name: str = "Учет заработной платы"
    version: str = "0.0.0"
    currency: str = "руб."
    date_format: str = "%d.%m.%Y"
    
    # UI настройки
    default_theme: str = "clam"
    font_family: str = "Segoe UI"
    font_size: int = 10

    # Web настройки
    web_host: str = "127.0.0.1"  # Безопасный локальный bind по умолчанию
    web_port: int = 5000
    web_debug: bool = False
    web_secret_key: str = ""  # Для сессий Flask
    web_api_key: str = ""  # API-ключ для опасных web-операций
    
    # Окружение
    is_production: bool = False
    production_warning: str = ""  # Текст предупреждения из prod.marker
    
    def __post_init__(self):
        # Пытаемся прочитать версию из файла
        self._read_version_from_file()
        
        # Определяем окружение
        self.is_production, marker_text = get_environment_info()
        self.production_warning = marker_text
        
        if self.is_production:
            logger.warning("[CONFIG] Предупреждение из prod.marker: %s", marker_text)
    
    def _read_version_from_file(self):
        """Читает версию из файла version.txt в корневой директории"""
        try:
            root_dir = Path(__file__).parent.parent.parent
            version_file = root_dir / "version.txt"
            
            if version_file.exists():
                with open(version_file, 'r', encoding='utf-8') as f:
                    version = f.read().strip()
                    if version:
                        self.version = version
            else:
                logger.warning("[CONFIG] Файл версии не найден: %s", version_file)
        except Exception:
            logger.exception("[CONFIG] Ошибка при чтении файла версии")
    
    @property
    def display_name_with_version(self) -> str:
        """Возвращает название приложения с версией и предупреждением для production"""
        base_name = f"{self.display_name} v.{self.version}"
        
        if self.is_production:
            # Добавляем предупреждение для production-окружения
            if self.production_warning:
                return f"{base_name} - {self.production_warning}"
            else:
                return f"{base_name} [PRODUCTION]"
        else:
            return base_name


# Синглтон конфигурации
class Config:
    """Singleton класс для глобального доступа к конфигурации"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Инициализация компонентов конфигурации
            cls._instance.db = DatabaseConfig()
            cls._instance.export = ExportConfig()
            cls._instance.logging = LoggingConfig()
            cls._instance.app = AppConfig()
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """Статический метод для получения экземпляра конфигурации"""
        return cls()


# Глобальный доступ к конфигурации
config = Config.get_instance()

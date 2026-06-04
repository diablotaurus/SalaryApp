"""
Основной модуль Flask приложения для веб-интерфейса.

Создает и конфигурирует Flask приложение, регистрирует blueprint'ы
маршрутов и настраивает секретный ключ для сессий.
"""

import os

from flask import Flask

from core.config.settings import config
from web.routes.errors import errors_bp
from web.routes.pages import pages_bp
from web.routes.salaries import salaries_bp
from web.routes.settings import settings_bp


def create_app() -> Flask:
    """
    Фабрика для создания Flask приложения.
    
    Returns:
        Flask: Сконфигурированное Flask приложение
        
    Процесс создания:
        1. Создание экземпляра Flask приложения
        2. Настройка секретного ключа для сессий
        3. Регистрация всех blueprint'ов
        4. Возврат готового приложения
    """
    # Создание экземпляра Flask приложения
    app = Flask(__name__)

    # Настройка секретного ключа для защиты сессий
    # Порядок приоритета:
    # 1. Переменная окружения SALARYAPP_WEB_SECRET_KEY
    # 2. Значение из конфигурации приложения
    # 3. Случайно сгенерированный ключ (для development)
    secret_key = os.getenv("SALARYAPP_WEB_SECRET_KEY") or config.app.web_secret_key
    if not secret_key:
        secret_key = os.urandom(24)  # Генерация случайного ключа (24 байта)
    app.secret_key = secret_key

    # Регистрация blueprint'ов (модулей маршрутов)
    # Порядок регистрации не имеет значения для маршрутизации
    app.register_blueprint(pages_bp)      # Статические страницы (главная, отчеты, настройки)
    app.register_blueprint(salaries_bp)   # API для работы с зарплатами
    app.register_blueprint(settings_bp)   # API для работы с настройками
    app.register_blueprint(errors_bp)     # Обработчики ошибок (404, 500)

    return app


# Глобальный экземпляр приложения для использования сервером WSGI
app = create_app()
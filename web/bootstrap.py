"""
Web startup helpers.
"""
from __future__ import annotations

import os
import sys
import logging

from core.config.settings import config
from core.database.migrations import apply_all_migrations
from web.app import create_app

logger = logging.getLogger(__name__)

def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def check_dependencies() -> bool:
    """Проверка наличия всех необходимых зависимостей из requirements.txt."""
    required_modules = [
        "flask",  # Web framework
        "pandas",  # Для ExportService
        "openpyxl",  # Для экспорта в Excel
        "matplotlib",  # Для графиков
        "aiogram",  # Для бота (импортируется в salary_api)
        "waitress",  # Production WSGI server
    ]
    missing_modules = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        logger.error("=" * 60)
        logger.error("ОШИБКА: отсутствуют необходимые модули:")
        for module in missing_modules:
            logger.error("  - %s", module)

        logger.error("\n" + "=" * 60)
        logger.error("РЕШЕНИЕ ДЛЯ WINDOWS:")
        logger.error("1. Установите Microsoft Visual C++ Build Tools:")
        logger.error("   https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        logger.error("   или используйте готовые сборки через pip:")

        if "pandas" in missing_modules:
            logger.error("\n2. Для pandas можно попробовать установить предварительно собранную версию:")
            logger.error("   pip install pandas --only-binary=pandas")

        if "matplotlib" in missing_modules:
            logger.error("\n3. Для matplotlib можно установить без зависимостей:")
            logger.error("   pip install matplotlib --only-binary=matplotlib")

        logger.error("\n4. Или попробуйте установить все зависимости одной командой:")
        logger.error("   pip install --only-binary=:all: -r requirements.txt")

        logger.error("\n5. Альтернативно, установите Anaconda или Miniconda, затем:")
        logger.error("   conda install -c conda-forge pandas matplotlib flask")

        logger.error("\n" + "=" * 60)
        return False

    return True


def main() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not check_dependencies():
        logger.info("Нажмите любую клавишу для выхода...")
        input()
        sys.exit(1)

    logger.info("Применение миграций базы данных...")
    apply_all_migrations()

    app = create_app()

    host = os.getenv("SALARYAPP_WEB_HOST", config.app.web_host)
    port = int(os.getenv("SALARYAPP_WEB_PORT", config.app.web_port))
    debug = _get_bool_env("SALARYAPP_WEB_DEBUG", config.app.web_debug)

    logger.info("Запуск web-приложения на http://%s:%s", host, port)
    if debug:
        app.run(host=host, port=port, debug=True)
    else:
        from waitress import serve

        serve(app, host=host, port=port, threads=4)


if __name__ == "__main__":
    main()

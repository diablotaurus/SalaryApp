@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ================================================================
echo Запуск веб-сервера SalaryApp
echo ================================================================

python --version >nul 2>&1
if errorlevel 1 (
    echo Ошибка: Python не найден в PATH.
    pause
    exit /b 1
)

python -c "import flask, waitress, openpyxl, matplotlib, aiogram" >nul 2>&1
if errorlevel 1 (
    echo Не установлены зависимости. Выполните:
    echo python -m pip install -r requirements.txt
    pause
    exit /b 1
)

python run_web.py
if errorlevel 1 (
    echo Веб-сервер завершился с ошибкой.
    pause
    exit /b 1
)

@echo off
chcp 1251 > nul
cd /d %~dp0

echo ================================================================
echo Проверка зависимостей для SalaryApp Web
echo ================================================================
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo Убедитесь, что Python установлен и добавлен в PATH.
    echo Скачать Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Проверка установленных модулей...
python -c "import flask, pandas, openpyxl, matplotlib, aiogram" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Обнаружены отсутствующие зависимости!
    echo.
    echo Установка зависимостей из requirements.txt...
    echo Это может занять несколько минут...
    echo.
    
    REM Пробуем установить обычным способом
    pip install -r requirements.txt
    
    if errorlevel 1 (
        echo.
        echo ================================================================
        echo НЕ УДАЛОСЬ УСТАНОВИТЬ ЗАВИСИМОСТИ!
        echo ================================================================
        echo.
        echo ПРОБЛЕМА: Некоторые пакеты требуют компилятора C/C++
        echo.
        echo РЕШЕНИЕ 1: Установите Microsoft Visual C++ Build Tools
        echo   Скачать: https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo   Установите, затем перезапустите bat-файл
        echo.
        echo РЕШЕНИЕ 2: Используйте предварительно собранные пакеты:
        echo   pip install --only-binary=:all: -r requirements.txt
        echo.
        echo РЕШЕНИЕ 3: Установите Anaconda/Miniconda, затем:
        echo   conda install -c conda-forge pandas matplotlib flask aiogram openpyxl
        echo.
        echo РЕШЕНИЕ 4: Установите зависимости вручную:
        echo   pip install flask==2.3.3
        echo   pip install pandas --only-binary=pandas
        echo   pip install matplotlib --only-binary=matplotlib
        echo   pip install aiogram==2.25.1
        echo   pip install openpyxl==3.1.2
        echo.
        pause
        exit /b 1
    )
    
    echo.
    echo Все зависимости успешно установлены!
)

echo.
echo ================================================================
echo Запуск web-приложения...
echo ================================================================
echo.
python run_web.py
pause
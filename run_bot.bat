@echo off
if exist "%SystemRoot%\System32\chcp.com" "%SystemRoot%\System32\chcp.com" 65001 >nul
cd /d "%~dp0"

echo ================================================================
echo Starting SalaryApp Telegram bot
echo ================================================================
echo.

REM Check Python availability
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found.
    echo Ensure Python is installed and available in PATH.
    pause
    exit /b 1
)

echo Checking installed modules...
python -c "import aiogram" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Missing dependencies detected.
    echo Installing dependencies from requirements.txt...
    echo.
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo FAILED TO INSTALL DEPENDENCIES!
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Starting bot...
echo Press CTRL+C to quit
echo.
cmd /c python run_bot.py

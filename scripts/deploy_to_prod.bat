@echo off
REM Launcher for the production deploy script (UTF-8 console for Cyrillic output).
chcp 65001 > nul
echo ============================================
echo   SalaryApp - deploy to PRODUCTION
echo ============================================
echo.

REM Check that Python is available.
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH!
    pause
    exit /b 1
)

REM Run the deploy script located next to this .bat. Extra args are passed through
REM (for example: deploy_to_prod.bat --dry-run).
python "%~dp0deploy_to_prod.py" %*
set EXIT_CODE=%errorlevel%

echo.
if %EXIT_CODE% EQU 0 (
    echo Done.
) else (
    echo Finished with error code: %EXIT_CODE%.
)
pause

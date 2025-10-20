@echo off
setlocal EnableDelayedExpansion

:: Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

:: Quick venv setup
if not exist "venv\Scripts\python.exe" (
    echo [*] Creating virtual environment...
    python -m venv venv --clear
    if errorlevel 1 (
        echo [!] Failed to create venv
        pause
        exit /b 1
    )
    echo [+] Virtual environment created
)

:: Activate venv
call venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
    echo [!] Failed to activate venv
    pause
    exit /b 1
)

:: Install dependencies
if exist requirements.txt (
    echo [*] Installing dependencies...
    pip install -q -r requirements.txt
)

:: Run application
echo [*] Starting Claude Backup Manager...
start "" pythonw -m app.main
exit

if errorlevel 1 (
    echo.
    echo [!] Application exited with error
)

pause

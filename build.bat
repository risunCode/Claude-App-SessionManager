@echo off
setlocal enableextensions enabledelayedexpansion

REM Build portable one-file EXE with bundled Python and modules
pushd "%~dp0"

set VENV_DIR=venv
set PYTHON_EXE=%VENV_DIR%\Scripts\python.exe
set PIP_EXE=%VENV_DIR%\Scripts\pip.exe
set PYINSTALLER_EXE=%VENV_DIR%\Scripts\pyinstaller.exe

if not exist "%PYTHON_EXE%" (
  echo [*] Creating virtual environment...
  where py >nul 2>nul
  if %ERRORLEVEL%==0 (
    py -3 -m venv "%VENV_DIR%"
  ) else (
    python -m venv "%VENV_DIR%"
  )
)

echo [*] Upgrading pip...
"%PYTHON_EXE%" -m pip install -U pip wheel setuptools

echo [*] Installing requirements...
"%PIP_EXE%" install -r requirements.txt

echo [*] Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [*] Building EXE...
set EXCLUDES=--exclude-module tkinter --exclude-module test --exclude-module tests --exclude-module distutils --exclude-module idlelib --exclude-module pip --exclude-module setuptools --exclude-module wheel

REM detect UPX
where upx >nul 2>nul
if %ERRORLEVEL%==0 (
  echo [*] UPX found. Enabling executable compression.
  set UPX_OPT=--upx-exclude vcruntime140.dll --upx-exclude ucrtbase.dll
) else (
  set UPX_OPT=
)

"%PYINSTALLER_EXE%" --noconfirm --clean --onefile --noconsole --optimize=2 --name ClaudeBackupManager %EXCLUDES% %UPX_OPT% app\main.py
if %ERRORLEVEL% NEQ 0 (
  echo [!] Build failed.
  popd
  exit /b 1
)

echo [*] Removing __pycache__ and *.pyc ...
for /d /r %%D in (__pycache__) do if exist "%%D" rmdir /s /q "%%D"
for /r %%F in (*.pyc) do del /q "%%F"

echo [✓] Build complete: dist\ClaudeBackupManager.exe
popd
exit /b 0

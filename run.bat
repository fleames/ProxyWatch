@echo off
REM ProxyWatch Launcher for Windows
REM Auto-activates venv and runs the dashboard

setlocal

set SCRIPT_DIR=%~dp0
set VENV_DIR=%SCRIPT_DIR%venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [!] Virtual environment not found at %VENV_DIR%
    echo     Set it up with: python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

REM Activate venv and run
call "%VENV_DIR%\Scripts\activate.bat"
python "%SCRIPT_DIR%main.py" %*
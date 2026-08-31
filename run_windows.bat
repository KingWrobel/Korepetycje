@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Najpierw uruchom setup_windows.bat
    pause
    exit /b 1
)

".venv\Scripts\python.exe" app.py

@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/5] Tworze srodowisko .venv...
    python -m venv .venv
    if errorlevel 1 goto :error
)

echo [2/5] Instaluje biblioteki...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

if not exist ".env" (
    echo [3/5] Tworze .env z .env.example...
    copy ".env.example" ".env" >nul
) else (
    echo [3/5] .env juz istnieje.
)

echo [4/5] Aktualizuje baze danych...
".venv\Scripts\python.exe" -m flask --app app db upgrade
if errorlevel 1 goto :error

echo [5/5] Tworze konto testowe...
".venv\Scripts\python.exe" seed.py
if errorlevel 1 goto :error

echo.
echo GOTOWE.
echo Uruchom teraz: run_windows.bat
exit /b 0

:error
echo.
echo Wystapil blad. Sprawdz komunikat powyzej.
exit /b 1

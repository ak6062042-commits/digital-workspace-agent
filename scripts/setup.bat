@echo off
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

echo ========================================================
echo     Digital Workspace Agent — Windows Setup Script
echo ========================================================

rem 1. Python Virtual Environment Setup
set VENV_DIR=%PROJECT_ROOT%\.venv
if not exist "%VENV_DIR%" (
    echo [+] Creating virtual environment in %VENV_DIR%...
    python -m venv "%VENV_DIR%"
) else (
    echo [*] Virtual environment already exists.
)

call "%VENV_DIR%\Scripts\activate.bat"

echo [+] Creating or validating secure local configuration...
python "%PROJECT_ROOT%\scripts\bootstrap_config.py"

echo [+] Upgrading pip and installing Python dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install -r "%PROJECT_ROOT%\backend\requirements.txt"
python -m pip install -r "%PROJECT_ROOT%\system-agent\local-agent\requirements.txt"
python -m pip install -r "%PROJECT_ROOT%\system-agent\floating-widget\requirements.txt"

rem 3. Database Initialization (demo data is intentionally opt-in)
echo [+] Initializing database schema...
python -c "from backend.db.db import init_db; init_db(); print('Database initialized')"

rem 4. Frontend Dependencies
where npm >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [+] Installing frontend dependencies...
    cd /d "%PROJECT_ROOT%\frontend"
    npm install
    cd /d "%PROJECT_ROOT%"
) else (
    echo [!] npm not found. Skipping frontend installation.
)

echo ========================================================
echo                  Setup Complete!
echo ========================================================
echo To activate virtual environment:
echo   .venv\Scripts\activate
echo To start backend server:
echo   scripts\run_backend.bat
echo To start local agent watcher:
echo   python system-agent\local-agent\watcher.py
echo To start React frontend:
echo   scripts\run_frontend.bat
echo To run tests:
echo   scripts\test.bat
echo ========================================================

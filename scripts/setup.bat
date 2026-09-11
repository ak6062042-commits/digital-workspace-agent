@echo off
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

echo ========================================================
echo     Digital Workspace Agent — Windows Setup Script
echo ========================================================

rem 1. Environment Configuration
if not exist "%PROJECT_ROOT%\.env" (
    echo [+] Creating .env from .env.example...
    copy "%PROJECT_ROOT%\.env.example" "%PROJECT_ROOT%\.env"
) else (
    echo [*] .env file already exists.
)

rem 2. Python Virtual Environment Setup
set VENV_DIR=%PROJECT_ROOT%\.venv
if not exist "%VENV_DIR%" (
    echo [+] Creating virtual environment in %VENV_DIR%...
    python -m venv "%VENV_DIR%"
) else (
    echo [*] Virtual environment already exists.
)

call "%VENV_DIR%\Scripts\activate.bat"

echo [+] Upgrading pip and installing Python dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install -r "%PROJECT_ROOT%\backend\requirements.txt"
python -m pip install -r "%PROJECT_ROOT%\system-agent\local-agent\requirements.txt"

rem 3. Database Initialization & Seeding
echo [+] Initializing SQLite database and seeding demo data...
python "%PROJECT_ROOT%\scripts\seed_data.py"

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
echo   uvicorn backend.main:app --port 8000 --reload
echo To start local agent watcher:
echo   python system-agent\local-agent\watcher.py
echo To start React frontend:
echo   cd frontend ^&^& npm run dev
echo ========================================================

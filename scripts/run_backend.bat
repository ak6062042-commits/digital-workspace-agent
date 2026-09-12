@echo off
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."
call .venv\Scripts\activate.bat
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

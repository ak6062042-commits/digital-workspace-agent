@echo off
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."
call .venv\Scripts\activate.bat
python -m unittest discover -s tests -v

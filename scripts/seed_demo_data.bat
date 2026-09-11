@echo off
echo === Seeding Demo Data for Digital Workspace Agent ===

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    set PYTHON_EXEC="%PROJECT_ROOT%\.venv\Scripts\python.exe"
) else (
    set PYTHON_EXEC=python
)

%PYTHON_EXEC% "%PROJECT_ROOT%\scripts\seed_data.py"

echo === Seeding Complete ===

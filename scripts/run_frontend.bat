@echo off
set SCRIPT_DIR=%~dp0
for /f "tokens=1,* delims==" %%A in ('findstr /b "VITE_API_TOKEN=" "%SCRIPT_DIR%..\.env"') do set "VITE_API_TOKEN=%%B"
if "%VITE_API_TOKEN%"=="" (
    echo VITE_API_TOKEN is missing. Run scripts\setup.bat first.
    exit /b 1
)
cd /d "%SCRIPT_DIR%..\frontend"
npm run dev

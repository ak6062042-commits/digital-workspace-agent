#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================================"
echo "    Digital Workspace Agent — System Setup Script"
echo "========================================================"

# 1. Python Virtual Environment Setup
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[-] Error: Python 3 was not found. Please install Python 3.10+."
    exit 1
fi

VENV_DIR="$PROJECT_ROOT/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[+] Creating virtual environment in $VENV_DIR..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
else
    echo "[*] Virtual environment already exists in $VENV_DIR."
fi

# Source virtualenv
source "$VENV_DIR/bin/activate"

echo "[+] Creating or validating secure local configuration..."
python "$PROJECT_ROOT/scripts/bootstrap_config.py"

echo "[+] Upgrading pip and installing Python dependencies..."
pip install --quiet --upgrade pip
pip install -r "$PROJECT_ROOT/backend/requirements.txt"
pip install -r "$PROJECT_ROOT/system-agent/local-agent/requirements.txt"

# 3. Database Initialization (demo data is intentionally opt-in)
echo "[+] Initializing database schema..."
python -c "from backend.db.db import init_db; init_db(); print('Database initialized')"

# 4. Frontend Dependencies (if Node is available and package.json is populated)
if command -v npm &>/dev/null; then
    if [ -s "$PROJECT_ROOT/frontend/package.json" ]; then
        echo "[+] Installing frontend dependencies..."
        cd "$PROJECT_ROOT/frontend"
        npm install
        cd "$PROJECT_ROOT"
    else
        echo "[*] frontend/package.json is currently empty (Track B pending). Skipping npm install."
    fi
else
    echo "[!] Node.js/npm not found. Skipping frontend package installation."
fi

echo ""
echo "========================================================"
echo "                 Setup Complete!"
echo "========================================================"
echo ""
echo "To activate your virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To start the backend server:"
echo "  scripts/run_backend.sh"
echo ""
echo "To start the OS local state watcher:"
echo "  python system-agent/local-agent/watcher.py"
echo ""
echo "To run the React frontend:"
echo "  scripts/run_frontend.sh"
echo ""
echo "To run tests:"
echo "  scripts/test.sh"
echo ""
echo "To load the Chrome extension companion:"
echo "  Load unpacked folder: system-agent/browser-extension in chrome://extensions"
echo "========================================================"

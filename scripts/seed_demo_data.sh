#!/usr/bin/env bash
set -e

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Seeding Demo Data for Digital Workspace Agent ==="

# Prefer python in .venv if available
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_EXEC="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="python3"
elif command -v python &>/dev/null; then
    PYTHON_EXEC="python"
else
    echo "Error: Python was not found on your PATH."
    exit 1
fi

"$PYTHON_EXEC" "$PROJECT_ROOT/scripts/seed_data.py"

echo "=== Seeding Complete ==="

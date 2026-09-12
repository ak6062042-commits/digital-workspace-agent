#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export VITE_API_TOKEN="$(sed -n 's/^VITE_API_TOKEN=//p' "$ROOT/.env" | head -n 1)"
if [ -z "$VITE_API_TOKEN" ]; then
  echo "VITE_API_TOKEN is missing. Run scripts/setup.sh first." >&2
  exit 1
fi
cd "$ROOT/frontend"
npm run dev

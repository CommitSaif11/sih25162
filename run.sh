#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-8000}"

# If running locally (not Codespaces), create venv and install deps
if [ ! -d ".venv" ]; then
  python3 -m venv .venv || python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate || true
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Starting API on http://127.0.0.1:${PORT}"
exec uvicorn src.app.main:app --host 0.0.0.0 --port "${PORT}"

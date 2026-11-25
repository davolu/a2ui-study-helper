#!/usr/bin/env bash
# One command: install everything, build the web app, start Study Helper.
#   ./run.sh            then open http://127.0.0.1:8000
# Needs Python 3.11+ and Node 20+.
set -euo pipefail
cd "$(dirname "$0")"

# Load settings from .env if you created one (cp .env.example .env). Nothing is printed.
if [[ -f .env ]]; then set -a; source ./.env; set +a; fi

echo "→ Python agent"
[[ -x .venv/bin/python ]] || python3 -m venv .venv
.venv/bin/pip install --quiet -r agent/requirements.txt

echo "→ React app"
(cd web && npm install --no-audit --no-fund --loglevel=error && npm run build --silent)

if [[ -z "${GEMINI_API_KEY:-}${GOOGLE_API_KEY:-}" ]]; then
  echo "  No GEMINI_API_KEY set: running the offline scripted agent."
fi
echo "→ Open http://127.0.0.1:${PORT:-8000}   (stop with Ctrl+C)"
cd agent && exec ../.venv/bin/uvicorn server:app --host 127.0.0.1 --port "${PORT:-8000}"

#!/usr/bin/env bash
# Coach Studio — one-command local startup.
# Brings up Postgres (via docker compose), installs deps, runs migrations,
# then starts the API with auto-reload at http://localhost:8000
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

PY=.venv/bin/python
PIP=.venv/bin/pip

# 1. Postgres (optional — only if docker is available and you use the bundled db)
if command -v docker >/dev/null 2>&1; then
	echo "==> Starting Postgres (docker compose)…"
	(cd "$ROOT" && docker compose up -d db) || echo "   (skipped: could not start db via docker compose)"
fi

# 2. Virtualenv + dependencies
if [ ! -x "$PY" ]; then
	echo "==> Creating virtualenv…"
	python3 -m venv .venv
fi
echo "==> Installing dependencies…"
"$PIP" install -q -r requirements.txt

# 3. Wait for the database, then apply migrations
echo "==> Applying database migrations…"
for attempt in $(seq 1 20); do
	if "$PY" -c "from app.database import engine; engine.connect().close()" 2>/dev/null; then
		break
	fi
	echo "   waiting for database… ($attempt/20)"
	sleep 1
done
.venv/bin/alembic upgrade head

# 4. Run the app (auto-reloads on code changes)
echo "==> Coach Studio running at http://localhost:8000  (Ctrl+C to stop)"
exec .venv/bin/uvicorn app.main:app --port 8000 --reload

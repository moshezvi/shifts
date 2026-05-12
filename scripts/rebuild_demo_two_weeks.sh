#!/usr/bin/env bash
# Reset the demo DB: stop uvicorn, delete SQLite, recreate May 10–23 2026 empty shifts,
# then random support assignments for that window.
#
# From repository root:
#   chmod +x scripts/rebuild_demo_two_weeks.sh   # once
#   ./scripts/rebuild_demo_two_weeks.sh
#
# Optional: DATABASE_PATH=/abs/path/to.db ./scripts/rebuild_demo_two_weeks.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export DATABASE_PATH="${DATABASE_PATH:-$ROOT/data/shifts.db}"

PYTHON="${ROOT}/backend/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

export PYTHONPATH="${ROOT}/backend:${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

echo "==> Stopping uvicorn (if any) matching app.main:app …"
pkill -f "uvicorn app.main:app" 2>/dev/null || true

echo "==> Removing database: $DATABASE_PATH"
rm -f "$DATABASE_PATH"

echo "==> Creating DB + seed + empty shifts 2026-05-10 .. 2026-05-23 …"
"$PYTHON" "$ROOT/scripts/rebuild_two_weeks_db.py"

echo "==> Random support assignments (same window) …"
"$PYTHON" "$ROOT/scripts/randomize_week_assignments.py" \
  --start-date 2026-05-10 \
  --end-date 2026-05-23 \
  --seed 42 \
  --clear-first

echo "==> Done. Start the app from backend/: uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

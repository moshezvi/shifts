#!/usr/bin/env python3
"""
Recreate SQLite from scratch: DDL, migrations, seed participants, then empty shift
rows for an inclusive operational-date range (defaults: 2026-05-10 .. 2026-05-23).

Run from repository root with repo root + backend on PYTHONPATH (the shell driver
sets this). DATABASE_PATH must point at the DB file to create (usually set by the shell).

Does not stop uvicorn or delete the file — use scripts/rebuild_demo_two_weeks.sh for that.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start",
        default="2026-05-10",
        help="First operational date (YYYY-MM-DD), inclusive",
    )
    parser.add_argument(
        "--end",
        default="2026-05-23",
        help="Last operational date (YYYY-MM-DD), inclusive",
    )
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    if end < start:
        print(f"ERROR: --end {args.end} must be >= --start {args.start}", file=sys.stderr)
        sys.exit(2)

    from app.database import database_path
    from db.bootstrap import create_bootstrap_connection, init_database

    path = database_path()
    conn = create_bootstrap_connection()
    try:
        init_database(conn, operational_date_range=(start, end))
    finally:
        conn.close()

    n = _shift_count(path)
    print(f"Database initialized: {path}")
    print(f"Operational dates: {args.start} .. {args.end} ({n} shift rows)")


def _shift_count(path: Path) -> int:
    import sqlite3

    conn = sqlite3.connect(path)
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM shift").fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


if __name__ == "__main__":
    main()

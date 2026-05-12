"""
Bootstrap the SQLite database: DDL, migrations, optional seed, shift horizon.

Run from repository root: `python -m db` (see `db.__main__` for PYTHONPATH).

Does not use `app.database.connect()` — that helper refuses to create a missing DB.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from app.database import database_path
from app.schedule import ensure_shift_slots, ensure_shift_slots_for_operational_range
from app.seed import seed_if_empty
from db.migrations import apply_ddl, apply_migrations


def create_bootstrap_connection() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database(
    conn: sqlite3.Connection,
    *,
    horizon_days: int = 14,
    operational_date_range: tuple[date, date] | None = None,
) -> None:
    """
    Idempotent: apply DDL, migrations, seed if empty, then fill shift rows.

    If ``operational_date_range`` is set ``(first, last)`` inclusive, inserts slots for
    those operational dates only (ignores ``horizon_days``). Otherwise uses
    ``ensure_shift_slots`` from the current instant's operational anchor.
    """
    apply_ddl(conn)
    apply_migrations(conn)
    seed_if_empty(conn)
    if operational_date_range is not None:
        lo, hi = operational_date_range
        ensure_shift_slots_for_operational_range(conn, lo, hi)
    else:
        ensure_shift_slots(conn, horizon_days=horizon_days)


def main() -> None:
    path = database_path()
    conn = create_bootstrap_connection()
    try:
        init_database(conn)
    finally:
        conn.close()
    print(f"Database initialized: {path}")

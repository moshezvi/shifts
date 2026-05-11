"""
Bootstrap the SQLite database: DDL, migrations, optional seed, shift horizon.

Run from repository root: `python -m db` (see `db.__main__` for PYTHONPATH).

Does not use `app.database.connect()` — that helper refuses to create a missing DB.
"""

from __future__ import annotations

import sqlite3

from app.database import database_path
from app.schedule import ensure_shift_slots
from app.seed import seed_if_empty
from db.migrations import apply_ddl, apply_migrations


def _connect_create_if_needed() -> sqlite3.Connection:
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
) -> None:
    """
    Idempotent: apply DDL, migrations, seed if empty, then fill shift rows.
    """
    apply_ddl(conn)
    apply_migrations(conn)
    seed_if_empty(conn)
    ensure_shift_slots(conn, horizon_days=horizon_days)


def main() -> None:
    path = database_path()
    conn = _connect_create_if_needed()
    try:
        init_database(conn)
    finally:
        conn.close()
    print(f"Database initialized: {path}")

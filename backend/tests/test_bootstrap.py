from __future__ import annotations

import sqlite3
from datetime import date

from db.bootstrap import create_bootstrap_connection, init_database


def test_init_database_idempotent(tmp_path, monkeypatch):
    path = tmp_path / "s.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))

    def run_init():
        conn = sqlite3.connect(path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        init_database(conn, horizon_days=2)
        conn.close()

    run_init()
    n1 = _shift_count(path)
    run_init()
    n2 = _shift_count(path)
    assert n1 == n2
    assert n1 >= 22  # 2 days × 11 slots


def test_init_database_operational_date_range(tmp_path, monkeypatch):
    path = tmp_path / "range.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    conn = create_bootstrap_connection()
    try:
        init_database(conn, operational_date_range=(date(2026, 5, 10), date(2026, 5, 23)))
    finally:
        conn.close()
    # 14 operational days × 11 slots/day
    assert _shift_count(path) == 154


def _shift_count(path) -> int:
    conn = sqlite3.connect(path)
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM shift").fetchone()
        return int(row[0])
    finally:
        conn.close()

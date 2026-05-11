from __future__ import annotations

import sqlite3

from db.bootstrap import init_database


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


def _shift_count(path) -> int:
    conn = sqlite3.connect(path)
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM shift").fetchone()
        return int(row[0])
    finally:
        conn.close()

"""Import the script module to exercise purge logic against SQLite."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SEED_SCRIPT = _REPO / "scripts" / "seed_random_supporters.py"


@pytest.fixture
def seed_mod():
    spec = importlib.util.spec_from_file_location("seed_random_supporters", _SEED_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["seed_random_supporters"] = mod
    spec.loader.exec_module(mod)
    try:
        yield mod
    finally:
        sys.modules.pop("seed_random_supporters", None)


def test_purge_synthetic_support_removes_matching_rows(tmp_path, seed_mod, monkeypatch):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE participant (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          display_name TEXT NOT NULL,
          email TEXT,
          role TEXT NOT NULL,
          gender TEXT NOT NULL,
          region TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE shift (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          operational_date TEXT NOT NULL,
          region TEXT NOT NULL,
          slot_label TEXT NOT NULL,
          sort_order INTEGER NOT NULL,
          starts_at TEXT NOT NULL,
          ends_at TEXT NOT NULL,
          assigned_participant_id INTEGER REFERENCES participant(id),
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE coverage_request (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          shift_id INTEGER NOT NULL REFERENCES shift(id),
          originator_participant_id INTEGER NOT NULL REFERENCES participant(id),
          status TEXT NOT NULL,
          approved_offer_id INTEGER,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          decided_at TEXT
        );
        CREATE TABLE offer (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          request_id INTEGER NOT NULL REFERENCES coverage_request(id),
          responder_participant_id INTEGER NOT NULL REFERENCES participant(id),
          offer_kind TEXT NOT NULL,
          swap_shift_id INTEGER,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          withdrawn_at TEXT
        );
        """
    )
    conn.execute(
        "INSERT INTO participant (display_name, email, role, gender, region) VALUES (?,?,?,?,?)",
        ("Demo Support X", "synth.abcd.il.0001@example.invalid", "support", "M", "IL"),
    )
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """
        INSERT INTO shift (
          operational_date, region, slot_label, sort_order,
          starts_at, ends_at, assigned_participant_id
        )
        VALUES ('2026-01-01','IL','08-10',1,
          '2026-01-01T06:00:00Z','2026-01-01T08:00:00Z',?)
        """,
        (pid,),
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """
        INSERT INTO coverage_request (shift_id, originator_participant_id, status)
        VALUES (?, ?, 'open')
        """,
        (sid, pid),
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """
        INSERT INTO offer (request_id, responder_participant_id, offer_kind, status)
        VALUES (?, ?, 'coverage', 'pending')
        """,
        (rid, pid),
    )
    conn.execute(
        "INSERT INTO participant (display_name, email, role, gender, region) VALUES (?,?,?,?,?)",
        ("יוסי כהן", "yossi@example.invalid", "support", "M", "IL"),
    )
    conn.commit()

    n = seed_mod.purge_synthetic_support(conn)
    assert n == 1
    assert conn.execute("SELECT COUNT(*) FROM participant").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM offer").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM coverage_request").fetchone()[0] == 0
    assert conn.execute("SELECT assigned_participant_id FROM shift").fetchone()[0] is None
    conn.close()

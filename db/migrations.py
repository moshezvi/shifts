"""
SQLite DDL and incremental migrations.

Run only via `python -m db` (see `db.bootstrap`). The web app does not apply these.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_DB_DIR = Path(__file__).resolve().parent


def schema_sql_path() -> Path:
    return _DB_DIR / "schema.sql"


def apply_ddl(conn: sqlite3.Connection) -> None:
    sql = schema_sql_path().read_text(encoding="utf-8")
    conn.executescript(sql)


_SHIFT_FAMILY_REBUILD_SQL = """
PRAGMA foreign_keys=OFF;
DROP TABLE IF EXISTS offer;
DROP TABLE IF EXISTS coverage_request;
DROP TABLE IF EXISTS shift;
PRAGMA foreign_keys=ON;

CREATE TABLE shift (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  operational_date TEXT NOT NULL,
  region TEXT NOT NULL CHECK (region IN ('IL', 'NA')),
  slot_label TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  starts_at TEXT NOT NULL,
  ends_at TEXT NOT NULL,
  assigned_participant_id INTEGER REFERENCES participant(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (operational_date, slot_label)
);

CREATE INDEX IF NOT EXISTS idx_shift_operational_date ON shift(operational_date);
CREATE INDEX IF NOT EXISTS idx_shift_region ON shift(region);
CREATE INDEX IF NOT EXISTS idx_shift_assigned ON shift(assigned_participant_id);
CREATE INDEX IF NOT EXISTS idx_shift_starts ON shift(starts_at);

CREATE TABLE coverage_request (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shift_id INTEGER NOT NULL REFERENCES shift(id),
  originator_participant_id INTEGER NOT NULL REFERENCES participant(id),
  status TEXT NOT NULL CHECK (status IN ('open', 'approved', 'cancelled')),
  approved_offer_id INTEGER,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  decided_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_request_shift ON coverage_request(shift_id);
CREATE INDEX IF NOT EXISTS idx_request_originator ON coverage_request(originator_participant_id);

CREATE TABLE offer (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id INTEGER NOT NULL REFERENCES coverage_request(id),
  responder_participant_id INTEGER NOT NULL REFERENCES participant(id),
  offer_kind TEXT NOT NULL CHECK (offer_kind IN ('coverage', 'swap')),
  swap_shift_id INTEGER REFERENCES shift(id),
  status TEXT NOT NULL CHECK (status IN ('pending', 'withdrawn')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  withdrawn_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_offer_request ON offer(request_id);
"""


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply additive migrations for existing SQLite files (idempotent)."""
    rows = conn.execute("PRAGMA table_info(participant)").fetchall()
    column_names = {r["name"] for r in rows}
    if "role" not in column_names:
        conn.execute(
            "ALTER TABLE participant ADD COLUMN role TEXT NOT NULL DEFAULT 'support'"
        )
        conn.execute(
            """
            UPDATE participant
            SET role = 'support'
            WHERE role IS NULL OR trim(role) = ''
            """
        )
        conn.execute(
            """
            UPDATE participant
            SET role = 'support'
            WHERE role NOT IN ('support', 'oncall', 'admin')
            """
        )

    rows = conn.execute("PRAGMA table_info(participant)").fetchall()
    column_names = {r["name"] for r in rows}
    if "gender" not in column_names:
        conn.execute(
            "ALTER TABLE participant ADD COLUMN gender TEXT NOT NULL DEFAULT 'M'"
        )
        conn.execute(
            """
            UPDATE participant
            SET gender = 'M'
            WHERE gender IS NULL OR trim(gender) = '' OR gender NOT IN ('M', 'F')
            """
        )
    if "region" not in column_names:
        conn.execute(
            "ALTER TABLE participant ADD COLUMN region TEXT NOT NULL DEFAULT 'IL'"
        )
        conn.execute(
            """
            UPDATE participant
            SET region = 'IL'
            WHERE region IS NULL OR trim(region) = ''
            """
        )
        conn.execute(
            """
            UPDATE participant
            SET region = 'IL'
            WHERE region NOT IN ('IL', 'NA')
            """
        )

    shift_tbl = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='shift'"
    ).fetchone()
    if shift_tbl:
        cols = {
            r["name"]
            for r in conn.execute("PRAGMA table_info(shift)").fetchall()
        }
        if cols and "operational_date" not in cols:
            conn.executescript(_SHIFT_FAMILY_REBUILD_SQL)

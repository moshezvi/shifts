from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _APP_DIR.parent.parent
_DEFAULT_DB_PATH = _REPO_ROOT / "data" / "shifts.db"


def database_path() -> Path:
    raw = os.environ.get("DATABASE_PATH", "").strip()
    return Path(raw) if raw else _DEFAULT_DB_PATH


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    # SQLite stores text as UTF-8; ensure we never coerce to a legacy encoding.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    schema_path = _APP_DIR / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
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


def migrate_schema(conn: sqlite3.Connection) -> None:
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
        # Normalize invalid legacy values if any slipped in.
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


def participant_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM participant").fetchone()
    return int(row["n"]) if row else 0

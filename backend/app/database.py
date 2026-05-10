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

    conn.execute(
        """
        UPDATE participant
        SET gender = 'F'
        WHERE id IN (2, 4, 6, 8, 10)
        """
    )


def participant_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM participant").fetchone()
    return int(row["n"]) if row else 0

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _APP_DIR.parent.parent
_DEFAULT_DB_PATH = _REPO_ROOT / "data" / "shifts.db"


class DatabaseNotInitializedError(RuntimeError):
    """SQLite missing. From repo root run: `python -m db`."""


def database_path() -> Path:
    raw = os.environ.get("DATABASE_PATH", "").strip()
    return Path(raw) if raw else _DEFAULT_DB_PATH


def connect() -> sqlite3.Connection:
    """
    Open an existing SQLite database. Does not create the file or run migrations.

    Use `python -m db` from the repository root to create/migrate/seed first.
    """
    path = database_path()
    if not path.is_file():
        raise DatabaseNotInitializedError(
            f"No database file at {path}. From the repository root, run: python -m db"
        )
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def participant_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM participant").fetchone()
    return int(row["n"]) if row else 0

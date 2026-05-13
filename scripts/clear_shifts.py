#!/usr/bin/env python3
"""
Nuclear shift reset that preserves participants.

Deletes shift-family data from SQLite:

- offer
- coverage_request
- shift

By default this only clears rows. Use --reinitialize to run the normal DB
bootstrap afterward, which recreates the rolling shift horizon and leaves
participants intact because seeding is skipped when participants already exist.

Run from repository root:

    python scripts/clear_shifts.py --dry-run
    python scripts/clear_shifts.py --yes
    python scripts/clear_shifts.py --yes --reinitialize
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_ROOT))

SHIFT_FAMILY_TABLES = ("offer", "coverage_request", "shift")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually delete shift-family rows. Required unless --dry-run is set.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print affected row counts without deleting anything.",
    )
    parser.add_argument(
        "--reinitialize",
        action="store_true",
        help="Run normal DB bootstrap after clearing shifts.",
    )
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=14,
        help="Shift horizon for --reinitialize (default: 14).",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.yes:
        print(
            "ERROR: this deletes all shifts and marketplace rows. "
            "Pass --yes or use --dry-run.",
            file=sys.stderr,
        )
        sys.exit(2)

    from app.database import connect, database_path
    from db.bootstrap import init_database

    path = database_path()
    if not path.is_file():
        print(f"ERROR: no database at {path}. Run: python -m db", file=sys.stderr)
        sys.exit(1)

    conn = connect()
    try:
        counts_before = _table_counts(conn)
        print(f"Database: {path}")
        print_counts("Before", counts_before)

        if args.dry_run:
            print("Dry run only; no rows deleted.")
            return

        conn.execute("BEGIN")
        try:
            for table in SHIFT_FAMILY_TABLES:
                if _table_exists(conn, table):
                    conn.execute(f"DELETE FROM {table}")
            conn.execute("COMMIT")
        except sqlite3.Error:
            conn.execute("ROLLBACK")
            raise

        counts_after_clear = _table_counts(conn)
        print_counts("After clear", counts_after_clear)

        if args.reinitialize:
            init_database(conn, horizon_days=max(args.horizon_days, 1))
            counts_after_init = _table_counts(conn)
            print_counts("After reinitialize", counts_after_init)
    finally:
        conn.close()


def _table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    out = {"participant": _count_if_exists(conn, "participant")}
    for table in SHIFT_FAMILY_TABLES:
        out[table] = _count_if_exists(conn, table)
    return out


def _count_if_exists(conn: sqlite3.Connection, table: str) -> int:
    if not _table_exists(conn, table):
        return 0
    row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(row[0]) if row else 0


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def print_counts(label: str, counts: dict[str, int]) -> None:
    print(
        f"{label}: participants={counts['participant']}, "
        f"shifts={counts['shift']}, "
        f"coverage_requests={counts['coverage_request']}, "
        f"offers={counts['offer']}"
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Insert additional synthetic **support** participants (IL / NA) into SQLite.

Run from repository root (default DB: data/shifts.db; override with DATABASE_PATH):

    source backend/.venv/bin/activate
    python scripts/seed_random_supporters.py --replace-synth
    python scripts/seed_random_supporters.py --replace-synth --dry-run

Defaults add **50** IL and **30** NA supporters (override with ``--il`` / ``--na``).
Display names are **Hebrew** (שם פרטי + משפחה); emails stay unique per run (batch token).

**``--replace-synth``** removes earlier script-generated supporters (emails matching
``synth%@example.invalid`` or names starting with ``Demo Support``), clears their
shift assignments, deletes related ``offer`` / ``coverage_request`` rows, then inserts
this run's batch in the same transaction.
"""

from __future__ import annotations

import argparse
import random
import secrets
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
sys.path.insert(0, str(_BACKEND))

# Hebrew given + family names (UTF-8). Combinations are shuffled for variety; uniqueness
# is guaranteed for up to len(GIVEN) * len(FAMILY) inserts per run.
GIVEN = (
    "אביגיל",
    "אור",
    "אורי",
    "אריה",
    "איילת",
    "אלון",
    "בנימין",
    "גל",
    "דוד",
    "דנה",
    "הדר",
    "יואב",
    "יונתן",
    "יעל",
    "יפעת",
    "יוסי",
    "ליאור",
    "לירון",
    "מאיה",
    "מיכל",
    "נועה",
    "נריה",
    "עמית",
    "עומר",
    "רועי",
    "רות",
    "שירה",
    "תמר",
)

FAMILY = (
    "אברהם",
    "אדרי",
    "בן דוד",
    "ברק",
    "גולן",
    "דהן",
    "הרשקוביץ",
    "ויצמן",
    "יצחק",
    "כהן",
    "לוי",
    "מזרחי",
    "משה",
    "נחום",
    "עבדי",
    "פריד",
    "קליין",
    "רוזן",
    "שלום",
    "שפירא",
)


def _unique_hebrew_display_names(rng: random.Random, n: int) -> list[str]:
    combos = [f"{g} {f}" for g in GIVEN for f in FAMILY]
    rng.shuffle(combos)
    if n <= len(combos):
        return combos[:n]
    out = combos[:]
    extra = n - len(combos)
    for i in range(extra):
        g, f = rng.choice(GIVEN), rng.choice(FAMILY)
        out.append(f"{g} {f} ({i + 1})")
    return out


def _synthetic_participant_ids(conn: sqlite3.Connection) -> list[int]:
    """IDs created by this script (or its older English demo names)."""
    rows = conn.execute(
        """
        SELECT id FROM participant WHERE
        (email IS NOT NULL AND lower(email) LIKE 'synth%@example.invalid')
        OR (display_name LIKE 'Demo Support%')
        ORDER BY id
        """
    ).fetchall()
    return [int(r["id"]) for r in rows]


def purge_synthetic_support(conn: sqlite3.Connection) -> int:
    """
    Remove synthetic supporters and dependent rows. Returns how many participants
    were deleted.
    """
    ids = _synthetic_participant_ids(conn)
    if not ids:
        return 0
    ph = ",".join("?" * len(ids))
    t = tuple(ids)
    conn.execute(
        f"""
        DELETE FROM offer WHERE responder_participant_id IN ({ph})
        OR request_id IN (
            SELECT id FROM coverage_request WHERE originator_participant_id IN ({ph})
        )
        """,
        t + t,
    )
    conn.execute(
        f"DELETE FROM coverage_request WHERE originator_participant_id IN ({ph})",
        t,
    )
    conn.execute(
        f"""
        UPDATE shift SET assigned_participant_id = NULL
        WHERE assigned_participant_id IN ({ph})
        """,
        t,
    )
    conn.execute(f"DELETE FROM participant WHERE id IN ({ph})", t)
    return len(ids)


def _planned_rows(
    *,
    il_count: int,
    na_count: int,
    batch: str,
    rng: random.Random,
) -> list[tuple[str, str, str, str]]:
    """Return (display_name, email, gender, region) rows."""
    total = il_count + na_count
    names = _unique_hebrew_display_names(rng, total)
    rows_il: list[tuple[str, str, str, str]] = []
    rows_na: list[tuple[str, str, str, str]] = []
    seq = 0
    for i in range(il_count):
        g = rng.choice("MF")
        seq += 1
        email = f"synth.{batch}.il.{seq:04d}@example.invalid"
        rows_il.append((names[i], email, g, "IL"))
    for j in range(na_count):
        g = rng.choice("MF")
        seq += 1
        email = f"synth.{batch}.na.{seq:04d}@example.invalid"
        rows_na.append((names[il_count + j], email, g, "NA"))
    rows = rows_il + rows_na
    rng.shuffle(rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--il",
        type=int,
        default=50,
        metavar="N",
        help="How many IL support participants to insert (default 50)",
    )
    parser.add_argument(
        "--na",
        type=int,
        default=30,
        metavar="N",
        help="How many NA support participants to insert (default 30)",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed (name order / gender)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts and sample rows without writing",
    )
    parser.add_argument(
        "--replace-synth",
        action="store_true",
        help="Delete prior script-generated supporters, then insert this batch (same transaction)",
    )
    args = parser.parse_args()

    if args.il < 0 or args.na < 0:
        print("ERROR: --il and --na must be non-negative.", file=sys.stderr)
        sys.exit(2)

    if args.il == 0 and args.na == 0:
        print("ERROR: at least one of --il or --na must be > 0.", file=sys.stderr)
        sys.exit(2)

    rng = random.Random(args.seed)
    batch = secrets.token_hex(3)

    from app.database import connect, database_path

    path = database_path()
    if not path.is_file():
        print(f"ERROR: no database at {path}. Run: python -m db", file=sys.stderr)
        sys.exit(1)

    planned = _planned_rows(il_count=args.il, na_count=args.na, batch=batch, rng=rng)

    print(f"Database: {path}")
    print(f"Planned inserts: IL={args.il}, NA={args.na} (total {len(planned)}) batch={batch}")

    if args.dry_run:
        conn = connect()
        try:
            if args.replace_synth:
                n = len(_synthetic_participant_ids(conn))
                print(
                    "(dry-run) would remove "
                    f"{n} synthetic supporter(s), then insert {len(planned)}."
                )
        finally:
            conn.close()
        for row in planned[:8]:
            print(f"  {row[3]} {row[2]}  {row[0]}")
        if len(planned) > 8:
            print(f"  ... and {len(planned) - 8} more")
        return

    conn = connect()
    try:
        conn.execute("BEGIN")
        try:
            removed = 0
            if args.replace_synth:
                removed = purge_synthetic_support(conn)
                print(f"Removed {removed} synthetic supporter(s).")
            for display_name, email, gender, region in planned:
                conn.execute(
                    """
                    INSERT INTO participant (display_name, email, role, gender, region)
                    VALUES (?, ?, 'support', ?, ?)
                    """,
                    (display_name, email, gender, region),
                )
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
        print(f"Committed {len(planned)} new support participants.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Load support volunteers and shift rows from SQLite, then assign each shift a random
volunteer from the matching region (IL / NA). Handy for demo / synthetic-looking data.

Run from repository root (default DB: data/shifts.db; override with DATABASE_PATH):

    source backend/.venv/bin/activate
    python scripts/randomize_week_assignments.py --dry-run
    python scripts/randomize_week_assignments.py --week-offset 0 --clear-first
    python scripts/randomize_week_assignments.py --start-date 2026-05-10 --end-date 2026-05-23

Options:
    --days N           operational days from today's anchor (default 7); not used with
                       --start-date/--end-date or --week-offset
    --week-offset N    Jerusalem Sun–Sat week (0=this week, 1=next); same idea as GET
                       /api/shifts?week_offset=N — not with --start-date/--end-date
    --start-date, --end-date   inclusive operational dates (YYYY-MM-DD); together
    --seed INT         RNG seed for reproducibility
    --dry-run          print planned assignments only, do not write
    --only-unassigned  skip shifts that already have an assignee
    --clear-first      set assignees to NULL for all shifts in the window, then fill
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
sys.path.insert(0, str(_BACKEND))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Operational days from today's anchor (default 7; not used with --start-date)",
    )
    parser.add_argument(
        "--start-date",
        metavar="YYYY-MM-DD",
        default=None,
        help="First operational date inclusive (use with --end-date)",
    )
    parser.add_argument(
        "--end-date",
        metavar="YYYY-MM-DD",
        default=None,
        help="Last operational date inclusive (use with --start-date)",
    )
    parser.add_argument(
        "--week-offset",
        type=int,
        default=None,
        metavar="N",
        help="Sun–Sat week in Asia/Jerusalem (0=this week); do not mix with --start-date",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print assignments without updating the database",
    )
    parser.add_argument(
        "--only-unassigned",
        action="store_true",
        help="Only consider shifts with no current assignee",
    )
    parser.add_argument(
        "--clear-first",
        action="store_true",
        help="Unassign everyone in the date window, then assign all shifts in that window",
    )
    args = parser.parse_args()

    if args.clear_first and args.only_unassigned:
        print("ERROR: use either --clear-first or --only-unassigned, not both.", file=sys.stderr)
        sys.exit(2)

    if (args.start_date is None) ^ (args.end_date is None):
        print(
            "ERROR: use both --start-date and --end-date together, or neither.",
            file=sys.stderr,
        )
        sys.exit(2)

    if args.week_offset is not None and (
        args.start_date is not None or args.end_date is not None
    ):
        print(
            "ERROR: do not combine --week-offset with --start-date/--end-date.",
            file=sys.stderr,
        )
        sys.exit(2)

    if args.seed is not None:
        random.seed(args.seed)

    from app.database import connect, database_path
    from app.schedule import calendar_week_range_sun_sat, operational_date_for_instant
    from app.shift_assignment import set_shift_assignment

    if args.week_offset is not None:
        start, end = calendar_week_range_sun_sat(args.week_offset)
    elif args.start_date is not None:
        start = date.fromisoformat(args.start_date)
        end = date.fromisoformat(args.end_date)
        if end < start:
            print("ERROR: --end-date must be >= --start-date.", file=sys.stderr)
            sys.exit(2)
    else:
        now = datetime.now(timezone.utc)
        start = operational_date_for_instant(now)
        end = start + timedelta(days=max(args.days, 1) - 1)

    start_s, end_s = start.isoformat(), end.isoformat()

    path = database_path()
    if not path.is_file():
        print(f"ERROR: no database at {path}. Run: python -m db", file=sys.stderr)
        sys.exit(1)

    conn = connect()
    try:
        supports = conn.execute(
            """
            SELECT id, region, display_name
            FROM participant
            WHERE role = 'support'
            ORDER BY id
            """
        ).fetchall()
        by_region: dict[str, list] = {"IL": [], "NA": []}
        for r in supports:
            reg = str(r["region"])
            if reg in by_region:
                by_region[reg].append(r)

        only_unassigned = args.only_unassigned and not args.clear_first
        shift_sql = """
            SELECT id, operational_date, region, slot_label, assigned_participant_id
            FROM shift
            WHERE operational_date >= ? AND operational_date <= ?
        """
        params: list = [start_s, end_s]
        if only_unassigned:
            shift_sql += " AND assigned_participant_id IS NULL"
        shift_sql += " ORDER BY operational_date ASC, sort_order ASC"

        shifts = conn.execute(shift_sql, params).fetchall()

        planned: list[tuple[int, int, str, str, str, str]] = []
        for row in shifts:
            rid = str(row["region"])
            pool = by_region.get(rid, [])
            if not pool:
                print(
                    f"skip shift {row['id']} ({row['operational_date']} {row['slot_label']} "
                    f"{rid}): no support volunteers in pool",
                    file=sys.stderr,
                )
                continue
            pick = random.choice(pool)
            pid, pname = int(pick["id"]), str(pick["display_name"])
            planned.append(
                (
                    int(row["id"]),
                    pid,
                    str(row["operational_date"]),
                    str(row["slot_label"]),
                    rid,
                    pname,
                )
            )

        print(f"Database: {path}")
        print(
            f"Window: operational {start_s} .. {end_s} "
            f"({len(shifts)} shift rows, {len(planned)} to assign)"
        )
        print(
            f"Support pools: IL={len(by_region['IL'])}, NA={len(by_region['NA'])} "
            f"(only support role can cover shifts)"
        )

        if args.dry_run:
            if args.clear_first:
                print("(dry-run) would clear assignees for all shifts in window, then:")
            for sid, pid, od, sl, reg, pname in planned[:25]:
                print(f"  shift {sid} {od} {sl} {reg} -> {pname} (id {pid})")
            if len(planned) > 25:
                print(f"  ... and {len(planned) - 25} more")
            return

        conn.execute("BEGIN")
        try:
            if args.clear_first:
                conn.execute(
                    """
                    UPDATE shift
                    SET assigned_participant_id = NULL
                    WHERE operational_date >= ? AND operational_date <= ?
                    """,
                    (start_s, end_s),
                )
            for sid, pid, _od, _sl, _reg, _pname in planned:
                set_shift_assignment(conn, sid, pid)
        except ValueError as e:
            conn.execute("ROLLBACK")
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        conn.execute("COMMIT")
        print(f"Committed {len(planned)} assignments.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

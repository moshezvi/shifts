from __future__ import annotations

import random
import sqlite3
from datetime import datetime, timedelta, timezone

# Hebrew sample names — UTF-8. Roles: support | oncall | admin.
# Regions: IL | NA — five volunteers NA, five IL (deterministic shuffle for stable seeds).

PARTICIPANT_ROWS: list[tuple[str, str | None, str, str]] = [
    ("יוסי כהן", "yossi@example.invalid", "support", "M"),
    ("דנה לוי", "dana@example.invalid", "support", "F"),
    ("עומר שפירא", "omer@example.invalid", "support", "M"),
    ("מיכל רוזן", "michal@example.invalid", "oncall", "F"),
    ("רועי אדרי", "roi@example.invalid", "oncall", "M"),
    ("גיא נחום", "guy@example.invalid", "admin", "F"),
    ("נועה ברק", "noa@example.invalid", "support", "F"),
    ("איתי גולן", "itai@example.invalid", "support", "F"),
    ("שירה בן דוד", "shira@example.invalid", "oncall", "F"),
    ("תמר קליין", "tamar@example.invalid", "admin", "F"),
]

_rng = random.Random(42)
_order = list(range(len(PARTICIPANT_ROWS)))
_rng.shuffle(_order)
_NA_INDICES = set(_order[:5])

PARTICIPANTS: list[tuple[str, str | None, str, str, str]] = [
    (*PARTICIPANT_ROWS[i], "NA" if i in _NA_INDICES else "IL")
    for i in range(len(PARTICIPANT_ROWS))
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def seed_if_empty(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) AS n FROM participant").fetchone()["n"] > 0:
        return

    conn.execute("BEGIN")
    try:
        for name, email, role, gender, region in PARTICIPANTS:
            conn.execute(
                """
                INSERT INTO participant (display_name, email, role, gender, region)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, email, role, gender, region),
            )

        # Support shifts only; split per region (IL / NA).
        base = _utc_now().replace(hour=9, minute=0, second=0, microsecond=0)
        shift_idx = 0
        for region in ("IL", "NA"):
            rows = conn.execute(
                """
                SELECT id FROM participant
                WHERE role = 'support' AND region = ?
                ORDER BY id ASC
                """,
                (region,),
            ).fetchall()
            ids = [int(r["id"]) for r in rows]
            if not ids:
                continue
            for j in range(3):
                shift_idx += 1
                start = base + timedelta(days=7 * (shift_idx - 1))
                end = start + timedelta(hours=8)
                assigned = ids[j % len(ids)]
                conn.execute(
                    """
                    INSERT INTO shift (label, starts_at, ends_at, assigned_participant_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        f"משמרת {shift_idx} ({region})",
                        start.isoformat(),
                        end.isoformat(),
                        assigned,
                    ),
                )

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

from __future__ import annotations

import random
import sqlite3

# Hebrew sample names — UTF-8. Roles: support | oncall | admin.
# Regions IL|NA: five NA / five IL (shuffle seed 42).

PARTICIPANT_ROWS: list[tuple[str, str | None, str, str]] = [
    ("יוסי כהן", "yossi@example.invalid", "support", "M"),
    ("דנה לוי", "dana@example.invalid", "support", "F"),
    ("עומר שפירא", "omer@example.invalid", "support", "M"),
    ("מיכל רוזן", "michal@example.invalid", "oncall", "F"),
    ("רועי אדרי", "roi@example.invalid", "oncall", "M"),
    ("גיא נחום", "guy@example.invalid", "admin", "M"),
    ("נועה ברק", "noa@example.invalid", "support", "F"),
    ("איתי גולן", "itai@example.invalid", "support", "M"),
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

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

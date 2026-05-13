"""
Shared rules for assigning a support volunteer to a shift slot (single or bulk).
"""

from __future__ import annotations

import sqlite3


class AssignmentConflictError(ValueError):
    """Raised when an assignment would violate a schedule invariant."""


def validate_one_shift_per_operational_day(
    conn: sqlite3.Connection,
    operational_date: str,
    participant_id: int,
) -> None:
    """Reject final states with one volunteer assigned twice on one operational day."""
    conflict = conn.execute(
        """
        SELECT operational_date, assigned_participant_id, COUNT(*) AS assignment_count
        FROM shift
        WHERE operational_date = ?
          AND assigned_participant_id = ?
        GROUP BY operational_date, assigned_participant_id
        HAVING COUNT(*) > 1
        LIMIT 1
        """,
        (operational_date, participant_id),
    ).fetchone()
    if conflict is None:
        return
    raise AssignmentConflictError(
        "participant already assigned on operational_date "
        f"{conflict['operational_date']}"
    )


def set_shift_assignment(
    conn: sqlite3.Connection,
    shift_id: int,
    assigned_participant_id: int | None,
    *,
    validate_daily_limit: bool = True,
) -> tuple[str, int] | None:
    """
    Update one shift row. Same rules as PATCH /api/shifts/{id}.

    Raises:
        AssignmentConflictError: participant already assigned on that day.
        ValueError: shift missing, participant missing, wrong role, or region mismatch.
    """
    meta = conn.execute(
        "SELECT id, operational_date, region FROM shift WHERE id = ?",
        (shift_id,),
    ).fetchone()
    if meta is None:
        raise ValueError(f"shift not found: {shift_id}")

    if assigned_participant_id is None:
        conn.execute(
            "UPDATE shift SET assigned_participant_id = NULL WHERE id = ?",
            (shift_id,),
        )
        return None

    prow = conn.execute(
        "SELECT id, region, role FROM participant WHERE id = ?",
        (assigned_participant_id,),
    ).fetchone()
    if prow is None:
        raise ValueError("participant not found")
    if prow["role"] != "support":
        raise ValueError("only support volunteers can be assigned to shifts")
    if prow["region"] != meta["region"]:
        raise ValueError(
            f"participant region {prow['region']} does not match "
            f"shift region {meta['region']}"
        )
    conn.execute(
        "UPDATE shift SET assigned_participant_id = ? WHERE id = ?",
        (assigned_participant_id, shift_id),
    )
    if validate_daily_limit:
        validate_one_shift_per_operational_day(
            conn,
            meta["operational_date"],
            assigned_participant_id,
        )
    return meta["operational_date"], assigned_participant_id

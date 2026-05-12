"""
Shared rules for assigning a support volunteer to a shift slot (single or bulk).
"""

from __future__ import annotations

import sqlite3


def set_shift_assignment(
    conn: sqlite3.Connection,
    shift_id: int,
    assigned_participant_id: int | None,
) -> None:
    """
    Update one shift row. Same rules as PATCH /api/shifts/{id}.

    Raises:
        ValueError: shift missing, participant missing, wrong role, or region mismatch.
    """
    meta = conn.execute(
        "SELECT id, region FROM shift WHERE id = ?",
        (shift_id,),
    ).fetchone()
    if meta is None:
        raise ValueError(f"shift not found: {shift_id}")

    if assigned_participant_id is None:
        conn.execute(
            "UPDATE shift SET assigned_participant_id = NULL WHERE id = ?",
            (shift_id,),
        )
        return

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

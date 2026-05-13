from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.requests import Request

from app.database import DatabaseNotInitializedError, connect, participant_count
from app.domain import REGIONS, SWAP_ELIGIBLE_ROLES
from app.schedule import calendar_week_range_sun_sat, operational_date_for_instant
from app.shift_assignment import (
    AssignmentConflictError,
    set_shift_assignment,
    validate_one_shift_per_operational_day,
)

_FRONTEND_DIR = _REPO_ROOT / "frontend"


class ShiftAssignmentBody(BaseModel):
    """Set to null to unassign."""

    assigned_participant_id: int | None = None


class BulkShiftAssignmentItem(BaseModel):
    shift_id: int
    assigned_participant_id: int | None = None


class BulkShiftAssignmentsBody(BaseModel):
    assignments: list[BulkShiftAssignmentItem] = Field(
        ...,
        max_length=2000,
        description="Each item updates one shift; all succeed or none (transaction).",
    )


def _shift_row_to_dict(r) -> dict:
    aid = r["assigned_participant_id"]
    return {
        "id": r["id"],
        "operational_date": r["operational_date"],
        "region": r["region"],
        "slot_label": r["slot_label"],
        "sort_order": r["sort_order"],
        "starts_at": r["starts_at"],
        "ends_at": r["ends_at"],
        "assigned_participant_id": aid,
        "assignee": (
            {"id": aid, "display_name": r["assignee_display_name"]}
            if aid is not None
            else None
        ),
    }


def _fetch_shift_joined(conn, shift_id: int):
    return conn.execute(
        """
        SELECT s.id, s.operational_date, s.region, s.slot_label, s.sort_order,
               s.starts_at, s.ends_at, s.assigned_participant_id,
               p.display_name AS assignee_display_name
        FROM shift s
        LEFT JOIN participant p ON p.id = s.assigned_participant_id
        WHERE s.id = ?
        """,
        (shift_id,),
    ).fetchone()


app = FastAPI(title="Shifts API")


@app.exception_handler(DatabaseNotInitializedError)
async def database_not_initialized_handler(
    request: Request, exc: DatabaseNotInitializedError
):
    return JSONResponse(
        status_code=503,
        content={
            "detail": str(exc),
            "hint": "From the repository root run: python -m db",
        },
    )


if _FRONTEND_DIR.is_dir():
    app.mount(
        "/ui/static",
        StaticFiles(directory=str(_FRONTEND_DIR / "static")),
        name="ui-static",
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return RedirectResponse(url="/ui")


@app.get("/ui")
def ui_week():
    """This week's shifts (HTML)."""
    path = _FRONTEND_DIR / "week.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="frontend/week.html missing")
    return FileResponse(path)


@app.get("/ui/by-user")
def ui_by_user():
    """Pick a user and see their shifts (HTML)."""
    path = _FRONTEND_DIR / "by-user.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="frontend/by-user.html missing")
    return FileResponse(path)


@app.get("/api/participants")
def list_participants():
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT id, display_name, email, role, gender, region, created_at
            FROM participant
            ORDER BY id ASC
            """
        ).fetchall()
        return JSONResponse(
            content={
                "participants": [
                    {
                        "id": r["id"],
                        "display_name": r["display_name"],
                        "email": r["email"],
                        "role": r["role"],
                        "gender": r["gender"],
                        "region": r["region"],
                        "created_at": r["created_at"],
                    }
                    for r in rows
                ],
            },
            media_type="application/json; charset=utf-8",
        )
    finally:
        conn.close()


@app.get("/api/shifts")
def list_shifts(
    days: int = 7,
    operational_date: str | None = None,
    participant_id: int | None = None,
    week_offset: int | None = None,
):
    """
    Shifts for operational anchor D (Jerusalem 08:00 through next day 08:00).

    Query modes (first match wins):

    - ``operational_date=YYYY-MM-DD`` — that operational day only.
    - ``week_offset`` (integer, e.g. 0=this civil week, 1=next, -1=previous) —
      Sunday–Saturday range in **Asia/Jerusalem** civil calendar (operational_date
      strings match those calendar dates). Ignores ``days``.
    - Otherwise ``days`` (1–60) from the current instant's operational anchor.
    """
    conn = connect()
    try:
        base_sql = """
            SELECT s.id, s.operational_date, s.region, s.slot_label, s.sort_order,
                   s.starts_at, s.ends_at, s.assigned_participant_id,
                   p.display_name AS assignee_display_name
            FROM shift s
            LEFT JOIN participant p ON p.id = s.assigned_participant_id
            """
        extra: dict = {}

        if operational_date:
            try:
                anchor = date.fromisoformat(operational_date)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="operational_date must be YYYY-MM-DD",
                ) from exc
            if participant_id is not None:
                rows = conn.execute(
                    base_sql
                    + """
                    WHERE s.operational_date = ?
                      AND s.assigned_participant_id = ?
                    ORDER BY s.sort_order ASC
                    """,
                    (anchor.isoformat(), participant_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    base_sql
                    + """
                    WHERE s.operational_date = ?
                    ORDER BY s.sort_order ASC
                    """,
                    (anchor.isoformat(),),
                ).fetchall()
        elif week_offset is not None:
            start, end = calendar_week_range_sun_sat(week_offset)
            start_s, end_s = start.isoformat(), end.isoformat()
            extra = {
                "week_start": start_s,
                "week_end": end_s,
                "week_offset": week_offset,
            }
            if participant_id is not None:
                rows = conn.execute(
                    base_sql
                    + """
                    WHERE s.operational_date >= ? AND s.operational_date <= ?
                      AND s.assigned_participant_id = ?
                    ORDER BY s.operational_date ASC, s.sort_order ASC
                    """,
                    (start_s, end_s, participant_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    base_sql
                    + """
                    WHERE s.operational_date >= ? AND s.operational_date <= ?
                    ORDER BY s.operational_date ASC, s.sort_order ASC
                    """,
                    (start_s, end_s),
                ).fetchall()
        else:
            d = min(max(days, 1), 60)
            start = operational_date_for_instant(datetime.now(timezone.utc))
            end = start + timedelta(days=d - 1)
            start_s, end_s = start.isoformat(), end.isoformat()
            if participant_id is not None:
                rows = conn.execute(
                    base_sql
                    + """
                    WHERE s.operational_date >= ? AND s.operational_date <= ?
                      AND s.assigned_participant_id = ?
                    ORDER BY s.operational_date ASC, s.sort_order ASC
                    """,
                    (start_s, end_s, participant_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    base_sql
                    + """
                    WHERE s.operational_date >= ? AND s.operational_date <= ?
                    ORDER BY s.operational_date ASC, s.sort_order ASC
                    """,
                    (start_s, end_s),
                ).fetchall()

        payload = {"shifts": [_shift_row_to_dict(r) for r in rows], **extra}
        return JSONResponse(
            content=payload,
            media_type="application/json; charset=utf-8",
        )
    finally:
        conn.close()


@app.patch("/api/shifts/bulk")
def bulk_assign_shifts(body: BulkShiftAssignmentsBody):
    """
    Apply many assignment updates in one transaction (all-or-nothing).
    PATCH fits partial updates to existing shift rows; body lists explicit changes only.
    """
    conn = connect()
    try:
        conn.execute("BEGIN")
        try:
            validation_pairs = set()
            for item in body.assignments:
                pair = set_shift_assignment(
                    conn,
                    item.shift_id,
                    item.assigned_participant_id,
                    validate_daily_limit=False,
                )
                if pair is not None:
                    validation_pairs.add(pair)
            for operational_date, participant_id in validation_pairs:
                validate_one_shift_per_operational_day(
                    conn,
                    operational_date,
                    participant_id,
                )
        except AssignmentConflictError as exc:
            conn.execute("ROLLBACK")
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            conn.execute("ROLLBACK")
            code = 404 if "shift not found" in str(exc).lower() else 400
            raise HTTPException(status_code=code, detail=str(exc)) from exc
        conn.execute("COMMIT")
        ids = [a.shift_id for a in body.assignments]
        return JSONResponse(
            content={"updated": len(body.assignments), "shift_ids": ids},
            media_type="application/json; charset=utf-8",
        )
    finally:
        conn.close()


@app.patch("/api/shifts/{shift_id}")
def assign_shift(shift_id: int, body: ShiftAssignmentBody):
    """Assign or unassign a volunteer to a shift slot. Region must match (IL/NA)."""
    conn = connect()
    try:
        try:
            set_shift_assignment(conn, shift_id, body.assigned_participant_id)
        except AssignmentConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            code = 404 if "shift not found" in str(exc).lower() else 400
            raise HTTPException(status_code=code, detail=str(exc)) from exc

        out = _fetch_shift_joined(conn, shift_id)
        return JSONResponse(
            content={"shift": _shift_row_to_dict(out)},
            media_type="application/json; charset=utf-8",
        )
    finally:
        conn.close()


@app.get("/api/meta/db")
def db_meta():
    """Smoke endpoint for dev: confirms seed ran."""
    conn = connect()
    try:
        n = participant_count(conn)
        return {
            "participant_count": n,
            "swap_eligible_roles": sorted(SWAP_ELIGIBLE_ROLES),
            "regions": sorted(REGIONS),
            "scheduling_note": "Swaps and shift pairing stay within the same region (IL vs NA).",
        }
    finally:
        conn.close()

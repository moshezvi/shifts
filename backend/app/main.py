from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.database import connect, init_schema, migrate_schema, participant_count
from app.domain import REGIONS, SWAP_ELIGIBLE_ROLES
from app.schedule import ensure_shift_slots, operational_date_for_instant
from app.seed import seed_if_empty

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_FRONTEND_DIR = _REPO_ROOT / "frontend"


class ShiftAssignmentBody(BaseModel):
    """Set to null to unassign."""

    assigned_participant_id: int | None = None


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect()
    try:
        init_schema(conn)
        migrate_schema(conn)
        seed_if_empty(conn)
        ensure_shift_slots(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="Shifts API", lifespan=lifespan)
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
):
    """Operational shifts: `operational_date` is the anchor D (08:00 Jerusalem → +1 day 08:00)."""
    conn = connect()
    try:
        base_sql = """
            SELECT s.id, s.operational_date, s.region, s.slot_label, s.sort_order,
                   s.starts_at, s.ends_at, s.assigned_participant_id,
                   p.display_name AS assignee_display_name
            FROM shift s
            LEFT JOIN participant p ON p.id = s.assigned_participant_id
            """
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
        else:
            d = min(max(days, 1), 60)
            start = operational_date_for_instant(datetime.now(timezone.utc))
            end = start + timedelta(days=d - 1)
            if participant_id is not None:
                rows = conn.execute(
                    base_sql
                    + """
                    WHERE s.operational_date >= ? AND s.operational_date <= ?
                      AND s.assigned_participant_id = ?
                    ORDER BY s.operational_date ASC, s.sort_order ASC
                    """,
                    (start.isoformat(), end.isoformat(), participant_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    base_sql
                    + """
                    WHERE s.operational_date >= ? AND s.operational_date <= ?
                    ORDER BY s.operational_date ASC, s.sort_order ASC
                    """,
                    (start.isoformat(), end.isoformat()),
                ).fetchall()

        return JSONResponse(
            content={"shifts": [_shift_row_to_dict(r) for r in rows]},
            media_type="application/json; charset=utf-8",
        )
    finally:
        conn.close()


@app.patch("/api/shifts/{shift_id}")
def assign_shift(shift_id: int, body: ShiftAssignmentBody):
    """Assign or unassign a volunteer to a shift slot. Region must match (IL/NA)."""
    conn = connect()
    try:
        meta = conn.execute(
            "SELECT id, region FROM shift WHERE id = ?",
            (shift_id,),
        ).fetchone()
        if meta is None:
            raise HTTPException(status_code=404, detail="shift not found")

        pid = body.assigned_participant_id
        if pid is None:
            conn.execute(
                "UPDATE shift SET assigned_participant_id = NULL WHERE id = ?",
                (shift_id,),
            )
        else:
            prow = conn.execute(
                "SELECT id, region, role FROM participant WHERE id = ?",
                (pid,),
            ).fetchone()
            if prow is None:
                raise HTTPException(
                    status_code=400,
                    detail="participant not found",
                )
            if prow["role"] != "support":
                raise HTTPException(
                    status_code=400,
                    detail="only support volunteers can be assigned to shifts",
                )
            if prow["region"] != meta["region"]:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"participant region {prow['region']} does not match "
                        f"shift region {meta['region']}"
                    ),
                )
            conn.execute(
                "UPDATE shift SET assigned_participant_id = ? WHERE id = ?",
                (pid, shift_id),
            )

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

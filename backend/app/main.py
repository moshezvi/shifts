from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import connect, init_schema, migrate_schema, participant_count
from app.domain import REGIONS, SWAP_ELIGIBLE_ROLES
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect()
    try:
        init_schema(conn)
        migrate_schema(conn)
        seed_if_empty(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="Shifts API", lifespan=lifespan)
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

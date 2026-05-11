from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Jerusalem")


def operational_date_for_instant(when: datetime) -> date:
    """Operational anchor D for `when`: window [D 08:00, D+1 08:00) in Jerusalem."""
    local = when.astimezone(TZ)
    if local.timetz() >= time(8, 0, tzinfo=TZ):
        return local.date()
    return local.date() - timedelta(days=1)


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class SlotSpec:
    slot_label: str
    sort_order: int
    region: str  # IL | NA
    start_local: datetime
    end_local: datetime


def slot_specs_for_operational_date(operational_date: date) -> list[SlotSpec]:
    """
    One operational day: Jerusalem [D 08:00, D+1 08:00).

    IL: 08–24 on calendar D (afternoon/evening); NA: after midnight until 08:00,
    still operational_date D (clock may show D+1).
    """
    d0 = operational_date
    d1 = operational_date + timedelta(days=1)

    def lt(day: date, hour: int, minute: int = 0) -> datetime:
        return datetime.combine(day, time(hour, minute), TZ)

    specs: list[SlotSpec] = []
    order = 0

    # IL daytime / evening (same calendar date D)
    il_pairs = [
        ("08-10", 2),
        ("10-12", 2),
        ("12-14", 2),
        ("14-16", 2),
        ("16-18", 2),
    ]
    t = lt(d0, 8, 0)
    for label, hours in il_pairs:
        order += 1
        end = t + timedelta(hours=hours)
        specs.append(SlotSpec(label, order, "IL", t, end))
        t = end

    # IL exceptions: 18–21, 21–24 (ends local midnight D+1)
    order += 1
    start_1821 = lt(d0, 18, 0)
    end_1821 = start_1821 + timedelta(hours=3)
    specs.append(SlotSpec("18-21", order, "IL", start_1821, end_1821))

    order += 1
    start_2124 = end_1821
    end_2124 = start_2124 + timedelta(hours=3)  # midnight D+1
    specs.append(SlotSpec("21-24", order, "IL", start_2124, end_2124))

    # NA overnight on calendar D+1, still operational_date D
    na_pairs = [
        ("00-02", 2),
        ("02-04", 2),
        ("04-06", 2),
        ("06-08", 2),
    ]
    t = end_2124  # 00:00 D+1 local
    for label, hours in na_pairs:
        order += 1
        end = t + timedelta(hours=hours)
        specs.append(SlotSpec(label, order, "NA", t, end))
        t = end

    assert t == lt(d1, 8, 0), "operational window must end at D+1 08:00 Jerusalem"
    return specs


def slots_as_rows(operational_date: date) -> list[dict]:
    rows: list[dict] = []
    od_s = operational_date.isoformat()
    for s in slot_specs_for_operational_date(operational_date):
        rows.append(
            {
                "operational_date": od_s,
                "region": s.region,
                "slot_label": s.slot_label,
                "sort_order": s.sort_order,
                "starts_at": _utc_iso(s.start_local),
                "ends_at": _utc_iso(s.end_local),
            }
        )
    return rows


def ensure_shift_slots(conn: sqlite3.Connection, horizon_days: int = 14) -> None:
    """Insert missing shift rows for the next `horizon_days` operational days."""
    now = datetime.now(timezone.utc)
    start = operational_date_for_instant(now)
    for i in range(horizon_days):
        od = start + timedelta(days=i)
        for row in slots_as_rows(od):
            conn.execute(
                """
                INSERT OR IGNORE INTO shift (
                  operational_date, region, slot_label, sort_order, starts_at, ends_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["operational_date"],
                    row["region"],
                    row["slot_label"],
                    row["sort_order"],
                    row["starts_at"],
                    row["ends_at"],
                ),
            )

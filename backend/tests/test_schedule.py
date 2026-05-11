from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest

from app.schedule import (
    operational_date_for_instant,
    slot_specs_for_operational_date,
    slots_as_rows,
)

TZ = ZoneInfo("Asia/Jerusalem")


def test_slot_specs_count_and_il_na_split():
    specs = slot_specs_for_operational_date(date(2026, 5, 10))
    assert len(specs) == 11
    il = [s for s in specs if s.region == "IL"]
    na = [s for s in specs if s.region == "NA"]
    assert len(il) == 7
    assert len(na) == 4
    assert [s.slot_label for s in specs[:5]] == [
        "08-10",
        "10-12",
        "12-14",
        "14-16",
        "16-18",
    ]
    assert specs[5].slot_label == "18-21" and specs[5].region == "IL"
    assert specs[6].slot_label == "21-24" and specs[6].region == "IL"
    assert [s.slot_label for s in specs[7:]] == ["00-02", "02-04", "04-06", "06-08"]
    assert all(s.region == "NA" for s in specs[7:])


def test_operational_window_ends_next_day_0800_jerusalem():
    specs = slot_specs_for_operational_date(date(2026, 5, 10))
    assert specs[-1].end_local == datetime.combine(
        date(2026, 5, 11), time(8, 0), TZ
    )


def test_slots_as_rows_operational_date_string():
    rows = slots_as_rows(date(2026, 6, 1))
    assert all(r["operational_date"] == "2026-06-01" for r in rows)
    assert rows[0]["region"] == "IL"
    assert rows[0]["starts_at"].endswith("Z")


@pytest.mark.parametrize(
    "utc_when, expected_anchor",
    [
        # 2026-05-10 12:00 UTC ≈ 15:00 Jerusalem same calendar day → anchor 2026-05-10
        (datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc), date(2026, 5, 10)),
        # Before 08:00 Jerusalem → previous calendar day as anchor
        (datetime(2026, 5, 10, 4, 0, tzinfo=timezone.utc), date(2026, 5, 9)),
    ],
)
def test_operational_date_for_instant(utc_when: datetime, expected_anchor: date):
    assert operational_date_for_instant(utc_when) == expected_anchor

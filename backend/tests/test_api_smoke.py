from __future__ import annotations


def _participants(client):
    return client.get("/api/participants").json()["participants"]


def _support_id(client, region: str = "IL") -> int:
    return next(
        p["id"]
        for p in _participants(client)
        if p["role"] == "support" and p["region"] == region
    )


def _support_ids(client, region: str = "IL") -> list[int]:
    return [
        p["id"]
        for p in _participants(client)
        if p["role"] == "support" and p["region"] == region
    ]


def _shifts_for_days(client, days: int = 1):
    r = client.get(f"/api/shifts?days={days}")
    assert r.status_code == 200
    return r.json()["shifts"]


def _clear_operational_date(client, operational_date: str) -> None:
    for shift in _shifts_for_days(client, days=3):
        if shift["operational_date"] != operational_date:
            continue
        r = client.patch(
            f"/api/shifts/{shift['id']}",
            json={"assigned_participant_id": None},
        )
        assert r.status_code == 200


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_participants_list(client):
    r = client.get("/api/participants")
    assert r.status_code == 200
    data = r.json()
    assert "participants" in data
    assert len(data["participants"]) >= 1
    p0 = data["participants"][0]
    assert {"id", "display_name", "role", "gender", "region"}.issubset(p0.keys())


def test_shifts_list(client):
    r = client.get("/api/shifts?days=1")
    assert r.status_code == 200
    shifts = r.json()["shifts"]
    assert len(shifts) == 11
    assert {s["region"] for s in shifts} == {"IL", "NA"}


def test_shifts_week_offset_returns_week_range_meta(client):
    r = client.get("/api/shifts?week_offset=0")
    assert r.status_code == 200
    data = r.json()
    assert "shifts" in data
    assert "week_start" in data and "week_end" in data
    assert data["week_offset"] == 0
    assert len(data["week_start"]) == 10
    assert data["week_start"] <= data["week_end"]


def test_patch_shift_assign_support(client):
    shifts = _shifts_for_days(client)
    il_shift = next(s for s in shifts if s["region"] == "IL")
    _clear_operational_date(client, il_shift["operational_date"])
    sid = il_shift["id"]
    support_id = _support_id(client)
    pr = client.patch(
        f"/api/shifts/{sid}",
        json={"assigned_participant_id": support_id},
    )
    assert pr.status_code == 200
    body = pr.json()["shift"]
    assert body["assigned_participant_id"] == support_id
    assert body["assignee"]["id"] == support_id


def test_patch_shift_rejects_same_support_twice_on_operational_date(client):
    shifts = _shifts_for_days(client)
    il_shifts = [s for s in shifts if s["region"] == "IL"][:2]
    assert len(il_shifts) >= 2
    _clear_operational_date(client, il_shifts[0]["operational_date"])
    support_id = _support_id(client)

    first = client.patch(
        f"/api/shifts/{il_shifts[0]['id']}",
        json={"assigned_participant_id": support_id},
    )
    assert first.status_code == 200
    second = client.patch(
        f"/api/shifts/{il_shifts[1]['id']}",
        json={"assigned_participant_id": support_id},
    )
    assert second.status_code == 409
    assert "already assigned" in second.json()["detail"]


def test_patch_shift_allows_same_support_on_different_operational_dates(client):
    shifts = _shifts_for_days(client, days=2)
    il_shifts = [s for s in shifts if s["region"] == "IL"]
    first = il_shifts[0]
    second = next(
        s for s in il_shifts if s["operational_date"] != first["operational_date"]
    )
    _clear_operational_date(client, first["operational_date"])
    _clear_operational_date(client, second["operational_date"])
    support_id = _support_id(client)

    first_response = client.patch(
        f"/api/shifts/{first['id']}",
        json={"assigned_participant_id": support_id},
    )
    assert first_response.status_code == 200
    second_response = client.patch(
        f"/api/shifts/{second['id']}",
        json={"assigned_participant_id": support_id},
    )
    assert second_response.status_code == 200


def test_patch_shift_allows_resaving_same_assignment_and_unassigning(client):
    shifts = _shifts_for_days(client)
    il_shift = next(s for s in shifts if s["region"] == "IL")
    _clear_operational_date(client, il_shift["operational_date"])
    support_id = _support_id(client)

    first = client.patch(
        f"/api/shifts/{il_shift['id']}",
        json={"assigned_participant_id": support_id},
    )
    assert first.status_code == 200
    second = client.patch(
        f"/api/shifts/{il_shift['id']}",
        json={"assigned_participant_id": support_id},
    )
    assert second.status_code == 200
    third = client.patch(
        f"/api/shifts/{il_shift['id']}",
        json={"assigned_participant_id": None},
    )
    assert third.status_code == 200
    assert third.json()["shift"]["assigned_participant_id"] is None


def test_bulk_assign_shifts(client):
    shifts = _shifts_for_days(client)
    il_shifts = [s for s in shifts if s["region"] == "IL"][:2]
    assert len(il_shifts) >= 2
    _clear_operational_date(client, il_shifts[0]["operational_date"])
    il_support = _support_ids(client)
    assert len(il_support) >= 2
    body = {
        "assignments": [
            {"shift_id": il_shifts[0]["id"], "assigned_participant_id": il_support[0]},
            {"shift_id": il_shifts[1]["id"], "assigned_participant_id": il_support[1]},
        ]
    }
    pr = client.patch("/api/shifts/bulk", json=body)
    assert pr.status_code == 200
    data = pr.json()
    assert data["updated"] == 2
    assert len(data["shift_ids"]) == 2


def test_bulk_assign_unknown_shift_returns_404(client):
    r = client.patch(
        "/api/shifts/bulk",
        json={"assignments": [{"shift_id": 999_999_999, "assigned_participant_id": 1}]},
    )
    assert r.status_code == 404


def test_bulk_assign_is_atomic_rollback(client):
    """If a later row fails validation, earlier updates in the same bulk must not persist."""
    shifts = _shifts_for_days(client)
    il_shift = next(s for s in shifts if s["region"] == "IL")
    _clear_operational_date(client, il_shift["operational_date"])
    sid = il_shift["id"]
    il_support_id = _support_id(client)
    assert (
        client.patch(
            f"/api/shifts/{sid}",
            json={"assigned_participant_id": None},
        ).status_code
        == 200
    )
    br = client.patch(
        "/api/shifts/bulk",
        json={
            "assignments": [
                {"shift_id": sid, "assigned_participant_id": il_support_id},
                {"shift_id": 999_999_999, "assigned_participant_id": il_support_id},
            ]
        },
    )
    assert br.status_code == 404
    after = next(
        s
        for s in client.get("/api/shifts?days=1").json()["shifts"]
        if s["id"] == sid
    )
    assert after["assigned_participant_id"] is None


def test_bulk_assign_rejects_same_support_twice_and_rolls_back(client):
    shifts = _shifts_for_days(client)
    il_shifts = [s for s in shifts if s["region"] == "IL"][:2]
    assert len(il_shifts) >= 2
    _clear_operational_date(client, il_shifts[0]["operational_date"])
    support_id = _support_id(client)

    br = client.patch(
        "/api/shifts/bulk",
        json={
            "assignments": [
                {
                    "shift_id": il_shifts[0]["id"],
                    "assigned_participant_id": support_id,
                },
                {
                    "shift_id": il_shifts[1]["id"],
                    "assigned_participant_id": support_id,
                },
            ]
        },
    )
    assert br.status_code == 409
    assert "already assigned" in br.json()["detail"]

    after = client.get("/api/shifts?days=1").json()["shifts"]
    by_id = {s["id"]: s for s in after}
    assert by_id[il_shifts[0]["id"]]["assigned_participant_id"] is None
    assert by_id[il_shifts[1]["id"]]["assigned_participant_id"] is None


def test_bulk_assign_allows_same_day_move_when_final_state_is_valid(client):
    shifts = _shifts_for_days(client)
    il_shifts = [s for s in shifts if s["region"] == "IL"][:2]
    assert len(il_shifts) >= 2
    _clear_operational_date(client, il_shifts[0]["operational_date"])
    support_id = _support_id(client)

    first = client.patch(
        f"/api/shifts/{il_shifts[0]['id']}",
        json={"assigned_participant_id": support_id},
    )
    assert first.status_code == 200

    br = client.patch(
        "/api/shifts/bulk",
        json={
            "assignments": [
                {
                    "shift_id": il_shifts[1]["id"],
                    "assigned_participant_id": support_id,
                },
                {"shift_id": il_shifts[0]["id"], "assigned_participant_id": None},
            ]
        },
    )
    assert br.status_code == 200

    after = client.get("/api/shifts?days=1").json()["shifts"]
    by_id = {s["id"]: s for s in after}
    assert by_id[il_shifts[0]["id"]]["assigned_participant_id"] is None
    assert by_id[il_shifts[1]["id"]]["assigned_participant_id"] == support_id


def test_ui_week_served(client):
    r = client.get("/ui")
    assert r.status_code == 200
    assert "משמרות" in r.text or "שבוע" in r.text

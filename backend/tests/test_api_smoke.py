from __future__ import annotations


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
    r = client.get("/api/shifts?days=1")
    assert r.status_code == 200
    shifts = r.json()["shifts"]
    il_shift = next(s for s in shifts if s["region"] == "IL")
    sid = il_shift["id"]
    r2 = client.get("/api/participants")
    participants = r2.json()["participants"]
    support_id = next(
        p["id"]
        for p in participants
        if p["role"] == "support" and p["region"] == "IL"
    )
    pr = client.patch(
        f"/api/shifts/{sid}",
        json={"assigned_participant_id": support_id},
    )
    assert pr.status_code == 200
    body = pr.json()["shift"]
    assert body["assigned_participant_id"] == support_id
    assert body["assignee"]["id"] == support_id


def test_bulk_assign_shifts(client):
    r = client.get("/api/shifts?days=1")
    assert r.status_code == 200
    shifts = r.json()["shifts"]
    il_shifts = [s for s in shifts if s["region"] == "IL"][:2]
    assert len(il_shifts) >= 2
    participants = client.get("/api/participants").json()["participants"]
    il_support = [p["id"] for p in participants if p["role"] == "support" and p["region"] == "IL"]
    assert len(il_support) >= 1
    body = {
        "assignments": [
            {"shift_id": il_shifts[0]["id"], "assigned_participant_id": il_support[0]},
            {"shift_id": il_shifts[1]["id"], "assigned_participant_id": il_support[-1]},
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
    r = client.get("/api/shifts?days=1")
    assert r.status_code == 200
    shifts = r.json()["shifts"]
    il_shift = next(s for s in shifts if s["region"] == "IL")
    sid = il_shift["id"]
    participants = client.get("/api/participants").json()["participants"]
    il_support_id = next(
        p["id"]
        for p in participants
        if p["role"] == "support" and p["region"] == "IL"
    )
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


def test_ui_week_served(client):
    r = client.get("/ui")
    assert r.status_code == 200
    assert "משמרות" in r.text or "שבוע" in r.text

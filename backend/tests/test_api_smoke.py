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


def test_ui_week_served(client):
    r = client.get("/ui")
    assert r.status_code == 200
    assert "משמרות" in r.text or "שבוע" in r.text

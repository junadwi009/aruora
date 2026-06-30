"""Phase 3d: milestone CRUD in Settings (scoped to the user's program)."""


def _program(client):
    """Create a program for the session user and return its milestones (with ids)."""
    client.post("/api/program", json={"lengthDays": 90})
    return client.get("/api/program/milestones").get_json()


def test_milestones_have_ids(client_with_seed):
    ms = _program(client_with_seed)
    assert len(ms) >= 1
    assert all("id" in m for m in ms)


def test_update_milestone(client_with_seed):
    ms = _program(client_with_seed)
    mid = ms[0]["id"]
    r = client_with_seed.put(f"/api/program/milestones/{mid}",
                             json={"title": "Custom goal", "dayTarget": 12,
                                   "targets": {"writing": "B2"}})
    assert r.status_code == 200
    updated = next(m for m in client_with_seed.get("/api/program/milestones").get_json() if m["id"] == mid)
    assert updated["title"] == "Custom goal"
    assert updated["dayTarget"] == 12
    assert updated["targets"]["writing"] == "B2"


def test_add_and_delete_milestone(client_with_seed):
    ms = _program(client_with_seed)
    n0 = len(ms)
    add = client_with_seed.post("/api/program/milestones",
                                json={"title": "Extra", "dayTarget": 99, "targets": {"reading": "C1"}})
    assert add.status_code == 200
    new_id = add.get_json()["id"]
    assert len(client_with_seed.get("/api/program/milestones").get_json()) == n0 + 1

    d = client_with_seed.delete(f"/api/program/milestones/{new_id}")
    assert d.status_code == 200
    assert len(client_with_seed.get("/api/program/milestones").get_json()) == n0


def test_cannot_edit_without_program(client_with_seed):
    # No program created → editing a bogus id is NOT_FOUND (scoped, not a crash)
    assert client_with_seed.put("/api/program/milestones/424242", json={"title": "x"}).status_code == 404
    assert client_with_seed.delete("/api/program/milestones/424242").status_code == 404

"""Phase 4a: data export + account deletion (scoped)."""


def test_export_returns_user_data(client_with_seed):
    # create some data for the session user
    client_with_seed.post("/api/writing/evaluate",
                          json={"taskType": "task2", "prompt": "p", "essay": "Essay text."})
    client_with_seed.post("/api/cards", json={"front": "word", "back": "meaning"})

    r = client_with_seed.get("/api/account/export")
    assert r.status_code == 200
    data = r.get_json()
    assert "profile" in data and data["profile"]["email"]
    assert len(data["attempts"]) >= 1
    assert len(data["cards"]) >= 1


def test_delete_account_removes_data_and_session(client_with_seed):
    client_with_seed.post("/api/cards", json={"front": "x", "back": "y"})
    assert client_with_seed.get("/api/cards").get_json()["stats"]["total"] == 1

    d = client_with_seed.delete("/api/account")
    assert d.status_code == 200
    # session is gone → /me 401; cards anonymous → empty
    assert client_with_seed.get("/api/account/me").status_code == 401
    assert client_with_seed.get("/api/cards").get_json()["stats"]["total"] == 0

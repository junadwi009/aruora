"""Phase 2d-4: flashcard + vocab routes."""


def test_card_crud_and_review(client_with_seed):
    # add single
    r = client_with_seed.post("/api/cards", json={"front": "ubiquitous", "back": "everywhere"})
    assert r.status_code == 200
    cid = r.get_json()["id"]

    # add batch
    rb = client_with_seed.post("/api/cards", json={"cards": [{"front": "a", "back": "1"}, {"front": "b", "back": "2"}]})
    assert rb.status_code == 200 and rb.get_json()["added"] == 2

    # list + stats
    lst = client_with_seed.get("/api/cards").get_json()
    assert lst["stats"]["total"] == 3
    assert len(lst["cards"]) == 3

    # due (all new are due)
    due = client_with_seed.get("/api/cards/due").get_json()
    assert len(due) == 3

    # review
    rv = client_with_seed.post(f"/api/cards/{cid}/review", json={"quality": 4})
    assert rv.status_code == 200 and rv.get_json()["reps"] == 1

    # delete
    assert client_with_seed.delete(f"/api/cards/{cid}").status_code == 200
    assert client_with_seed.delete("/api/cards/999999").status_code == 404


def test_vocab_stub(client_with_seed):
    r = client_with_seed.post("/api/vocab", json={"topic": "environment", "level": "B1"})
    assert r.status_code == 200
    b = r.get_json()
    assert "words" in b and b["stub"] is True

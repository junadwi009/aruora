"""Phase 2d-3: pronunciation drill routes (stub mode)."""


def test_pronounce_sentence_stub(client_with_seed):
    r = client_with_seed.post("/api/pronounce/sentence", json={"level": "B1"})
    assert r.status_code == 200
    b = r.get_json()
    assert "text" in b and "tips" in b and b["stub"] is True


def test_pronounce_feedback_stub(client_with_seed):
    r = client_with_seed.post(
        "/api/pronounce/feedback",
        json={"target": "The cat sat", "transcript": "the cat sat", "accuracy": 100, "missed": []},
    )
    assert r.status_code == 200
    b = r.get_json()
    assert "summary" in b and b["stub"] is True

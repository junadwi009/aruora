"""
Phase 2c: persistence on evaluate + history/trends read endpoints.
Uses the client_with_seed fixture (in-memory SQLite Repository + stub gateway).
"""


def test_writing_evaluate_persists_and_returns_saved_id(client_with_seed):
    r = client_with_seed.post(
        "/api/writing/evaluate",
        json={"taskType": "task2", "prompt": "p", "essay": "My essay text here."},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert isinstance(body.get("savedId"), int)


def test_speaking_evaluate_persists_and_returns_saved_id(client_with_seed):
    r = client_with_seed.post(
        "/api/speaking/evaluate",
        json={"part": "part2", "question": "Describe a book", "transcript": "I read..."},
    )
    assert r.status_code == 200
    assert isinstance(r.get_json().get("savedId"), int)


def test_history_list_and_detail(client_with_seed):
    # create one writing attempt
    saved = client_with_seed.post(
        "/api/writing/evaluate",
        json={"taskType": "task2", "prompt": "Prompt X", "essay": "Body Y here."},
    ).get_json()["savedId"]

    lst = client_with_seed.get("/api/history/attempts?type=writing")
    assert lst.status_code == 200
    rows = lst.get_json()
    assert any(row["id"] == saved for row in rows)
    assert rows[0]["type"] == "writing" and "overall" in rows[0]

    detail = client_with_seed.get(f"/api/history/attempt/{saved}")
    assert detail.status_code == 200
    d = detail.get_json()
    assert d["id"] == saved
    assert d["prompt"] == "Prompt X"
    assert "bands" in d and "cefr" in d


def test_history_detail_404(client_with_seed):
    r = client_with_seed.get("/api/history/attempt/424242")
    assert r.status_code == 404
    assert r.get_json()["error"]["code"] == "NOT_FOUND"


def test_stats_trends_shape(client_with_seed):
    client_with_seed.post(
        "/api/writing/evaluate",
        json={"taskType": "task2", "prompt": "p", "essay": "Essay one."},
    )
    r = client_with_seed.get("/api/stats/trends")
    assert r.status_code == 200
    tr = r.get_json()
    assert "writing" in tr and "speaking" in tr
    assert len(tr["writing"]) >= 1
    assert "overall" in tr["writing"][0]

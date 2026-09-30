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
    assert set(tr) >= {"writing", "speaking", "reading", "listening"}
    assert tr["writing"] == []


def test_practice_attempt_persists_with_server_accuracy_summary(client_with_seed):
    start = client_with_seed.post(
        "/api/practice/start",
        json={"skill": "reading", "band": "B2"},
    )
    assert start.status_code == 200

    packet = start.get_json()

    assert packet["skill"] == "reading"
    assert packet["scoringMethod"] == "practice-accuracy-v1"
    assert isinstance(packet["practiceId"], str)
    assert packet["practiceId"]
    assert packet["questions"]

    assert all(
        "answer" not in q and "explanation" not in q
        for q in packet["questions"]
    )

    answers = [q["options"][0] for q in packet["questions"]]

    r = client_with_seed.post(
        "/api/practice/attempt",
        json={
            "practiceId": packet["practiceId"],
            "answers": answers,
        },
    )

    assert r.status_code == 200

    result = r.get_json()

    assert isinstance(result["savedId"], int)
    assert result["scoringMethod"] == "practice-accuracy-v1"
    assert isinstance(result["accuracyPct"], (int, float))

    rows = client_with_seed.get(
        "/api/history/attempts?type=reading"
    ).get_json()

    row = next(
        x for x in rows
        if x["id"] == result["savedId"]
    )

    assert row["overall"] is None
    assert row["scoreMethod"] == "server_accuracy"
    assert row["accuracyPct"] == result["accuracyPct"]

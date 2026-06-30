"""Phase 2d-1: guided-lesson routes (today / generate / by-day). Stub mode."""


def test_lesson_today_computes_focus_day(client_with_seed):
    r = client_with_seed.get("/api/lesson/today")
    assert r.status_code == 200
    b = r.get_json()
    # no skill_levels → focus defaults to writing; no program → day 1
    assert b["day"] == 1
    assert b["focus"] == "writing"
    assert b["skill"] == "writing"
    assert b["band"]  # some band string
    # lessons are per-user and generated on demand → none cached yet
    assert b["lesson"] is None


def test_lesson_today_reflects_generated(client_with_seed):
    client_with_seed.post("/api/lesson/generate", json={"day": 1, "focus": "writing", "band": "B1"})
    b = client_with_seed.get("/api/lesson/today").get_json()
    assert b["lesson"] is not None and "goal" in b["lesson"]


def test_lesson_by_day_null_then_generated(client_with_seed):
    # day 2 not cached yet
    assert client_with_seed.get("/api/lesson/2").get_json()["lesson"] is None

    gen = client_with_seed.post(
        "/api/lesson/generate", json={"day": 2, "focus": "listening", "band": "B1"}
    )
    assert gen.status_code == 200
    body = gen.get_json()
    assert body["day"] == 2 and body["focus"] == "listening"
    assert "goal" in body["lesson"]

    # now cached
    again = client_with_seed.get("/api/lesson/2").get_json()
    assert again["lesson"] is not None and "goal" in again["lesson"]


def test_lesson_generate_idempotent_without_force(client_with_seed):
    first = client_with_seed.post("/api/lesson/generate", json={"day": 3, "focus": "writing", "band": "B1"}).get_json()
    # second call without force returns the SAME cached lesson
    second = client_with_seed.post("/api/lesson/generate", json={"day": 3, "focus": "writing", "band": "B1"}).get_json()
    assert first["lesson"] == second["lesson"]


def test_lesson_stub_has_lesson_shape(client_with_seed):
    body = client_with_seed.post(
        "/api/lesson/generate", json={"day": 5, "focus": "speaking", "band": "B1"}
    ).get_json()
    lesson = body["lesson"]
    for key in ("goal", "teach", "exercises", "produce", "review"):
        assert key in lesson

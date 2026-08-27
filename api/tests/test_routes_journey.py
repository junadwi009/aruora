"""
Integration tests for onboarding → placement start/submit → skill-levels journey.
"""


def test_onboarding_then_start(client_with_seed):
    r = client_with_seed.post("/api/onboarding", json={"name": "A", "goal": "work", "targetBand": 6.5})
    assert r.status_code == 200
    body = r.get_json()
    # OnboardingOut alias: targetBand must be camelCase in the response
    assert body["targetBand"] == 6.5
    s = client_with_seed.post("/api/placement/start", json={})
    body = s.get_json()
    assert body["comboId"] in (1, 2)
    # served items must NOT leak answer keys
    assert all("answer" not in it["payload"] for it in body["items"])


def test_onboarding_validation_422(client_with_seed):
    r = client_with_seed.post("/api/onboarding", json={"name": "A", "goal": "vacation", "targetBand": 6.5})
    assert r.status_code == 422
    assert r.get_json()["error"]["code"] == "VALIDATION"


def test_onboarding_exam_month_normalized(client_with_seed):
    """WS23: optional exam month (YYYY-MM) is stored as a full ISO date."""
    r = client_with_seed.post(
        "/api/onboarding",
        json={"name": "A", "goal": "work", "targetBand": 6.5, "examDate": "2027-03"},
    )
    assert r.status_code == 200
    me = client_with_seed.get("/api/account/me").get_json()
    assert me["examDate"] == "2027-03-01"


def test_onboarding_exam_month_bad_format_422(client_with_seed):
    r = client_with_seed.post(
        "/api/onboarding",
        json={"name": "A", "goal": "work", "targetBand": 6.5, "examDate": "March 2027"},
    )
    assert r.status_code == 422


def test_submit_seeds_skill_levels(client_with_seed):
    client_with_seed.post("/api/onboarding", json={"name": "A", "goal": "work", "targetBand": 6.5})
    start = client_with_seed.post("/api/placement/start", json={}).get_json()
    combo_id = start["comboId"]
    # submit empty answers + a writing/speaking sample so all 4 skills resolve
    payload = {
        "comboId": combo_id,
        "answers": {},
        "writingSamples": {"taskType": "task2", "prompt": "p", "essay": "hello world"},
        "speakingText": "I think so.",
    }
    res = client_with_seed.post("/api/placement/submit", json=payload)
    assert res.status_code == 200
    body = res.get_json()
    assert set(body["perSkill"].keys()) == {"listening", "reading", "writing", "speaking"}
    # PlacementResultOut contract: all top-level camelCase fields present
    assert "overallBand" in body
    assert "cefr" in body
    assert "gapToTarget" in body
    levels = client_with_seed.get("/api/skill-levels").get_json()
    assert len(levels) == 4

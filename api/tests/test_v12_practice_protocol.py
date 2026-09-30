"""Full Flask integration regression gates. Run in the assembled repository.
These tests are supplied, not counted in the isolated-container pass results.
"""

def test_old_client_scored_protocol_is_closed(client_with_seed):
    c = client_with_seed
    assert c.get("/api/practice/set?skill=reading").status_code == 410
    assert c.post("/api/practice/attempt", json={"skill":"reading","band":9,"correct":40,"total":40}).status_code == 422
    assert c.post("/api/mocks", json={"listening":9,"reading":9,"overall":9}).status_code == 410


def test_server_receipt_hides_answers_and_submission_is_idempotent(client_with_seed):
    c = client_with_seed
    response = c.post("/api/practice/start", json={"skill":"reading","band":"B1"})
    assert response.status_code == 200, response.get_json()
    task = response.get_json()
    assert task["questions"]
    assert all("answer" not in q and "explanation" not in q for q in task["questions"])
    body = {"practiceId":task["practiceId"], "answers":[""]*len(task["questions"])}
    first = c.post("/api/practice/attempt", json=body)
    second = c.post("/api/practice/attempt", json=body)
    assert first.status_code == second.status_code == 200
    assert first.get_json()["savedId"] == second.get_json()["savedId"]
    assert first.get_json()["correct"] == 0
    detail = c.get(f"/api/history/attempt/{first.get_json()['savedId']}").get_json()
    assert detail["bands"] == {}
    assert detail["scoreMetadata"]["scoreMethod"] == "server_accuracy"


def test_profile_privilege_and_invalid_targets_are_rejected(client_with_seed):
    c = client_with_seed
    for body in ({"emailVerified":True},{"isAdmin":True},{"targetBand":6.25},{"skillTargets":{"reading":"C2"}}):
        assert c.patch("/api/account/profile",json=body).status_code == 422

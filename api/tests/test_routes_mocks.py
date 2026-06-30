"""Phase 2d-2: mock-test persistence routes."""


def test_post_and_get_mocks(client_with_seed):
    r = client_with_seed.post("/api/mocks", json={"listening": 6.0, "reading": 7.0, "overall": 6.5})
    assert r.status_code == 200
    assert isinstance(r.get_json()["id"], int)

    lst = client_with_seed.get("/api/mocks")
    assert lst.status_code == 200
    rows = lst.get_json()
    assert len(rows) == 1
    assert rows[0]["overall"] == 6.5 and rows[0]["listening"] == 6.0

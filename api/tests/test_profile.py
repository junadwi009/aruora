"""Phase 3e: profile detail + avatar + change password."""


def test_update_profile_and_me(client_with_seed):
    r = client_with_seed.patch("/api/account/profile",
                               json={"name": "Arjuna", "country": "Indonesia",
                                     "examDate": "2026-09-01", "bio": "Targeting 7.0"})
    assert r.status_code == 200
    me = client_with_seed.get("/api/account/me").get_json()
    assert me["name"] == "Arjuna"
    assert me["country"] == "Indonesia"
    assert me["examDate"] == "2026-09-01"
    assert me["bio"] == "Targeting 7.0"


def test_update_targets(client_with_seed):
    r = client_with_seed.patch("/api/account/profile",
                               json={"targetBand": 7.0, "skillTargets": {"writing": "C1", "speaking": "B2"}})
    assert r.status_code == 200
    me = client_with_seed.get("/api/account/me").get_json()
    assert me["targetBand"] == 7.0
    assert me["skillTargets"]["writing"] == "C1"


def test_avatar_upload(client_with_seed):
    data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="
    r = client_with_seed.post("/api/account/avatar", json={"dataUrl": data_url})
    assert r.status_code == 200
    assert client_with_seed.get("/api/account/me").get_json()["avatar"] == data_url


def test_avatar_rejects_non_image(client_with_seed):
    r = client_with_seed.post("/api/account/avatar", json={"dataUrl": "data:text/plain;base64,aGk="})
    assert r.status_code == 422


def test_change_password(client_with_seed):
    # conftest registered tester@example.com / secret123
    bad = client_with_seed.post("/api/account/password",
                                json={"currentPassword": "wrong", "newPassword": "newsecret1"})
    assert bad.status_code == 401

    short = client_with_seed.post("/api/account/password",
                                  json={"currentPassword": "secret123", "newPassword": "abc"})
    assert short.status_code == 422

    ok = client_with_seed.post("/api/account/password",
                               json={"currentPassword": "secret123", "newPassword": "newsecret1"})
    assert ok.status_code == 200

    # old password no longer works; new one does
    client_with_seed.post("/api/account/logout")
    assert client_with_seed.post("/api/account/login",
                                 json={"email": "tester@example.com", "password": "secret123"}).status_code == 401
    assert client_with_seed.post("/api/account/login",
                                 json={"email": "tester@example.com", "password": "newsecret1"}).status_code == 200

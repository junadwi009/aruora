"""Phase 2d-2: mock-test persistence routes."""


def test_post_mocks_legacy_protocol_is_gone(client_with_seed):
    r = client_with_seed.post(
        "/api/mocks",
        json={
            "listening": 6.0,
            "reading": 7.0,
            "overall": 6.5,
        },
    )

    assert r.status_code == 410
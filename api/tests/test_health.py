from app import create_app

def test_health_ok():
    app = create_app({"TESTING": True})
    client = app.test_client()
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["llmMode"] == "stub"
    assert body["providerConfigured"] is False
    assert body["asrReady"] is False


def test_health_asr_ready_reflects_probe(monkeypatch):
    from app.routes import health as health_route

    monkeypatch.setattr(health_route, "asr_ready", lambda cfg: True)
    app = create_app({"TESTING": True})
    r = app.test_client().get("/api/health")
    assert r.get_json()["asrReady"] is True

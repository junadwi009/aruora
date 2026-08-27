from app import create_app

def test_health_ok():
    # Deterministic overrides: asrReady depends on whether faster-whisper is
    # importable (it IS in any full `pip install -r requirements.txt`, e.g. CI),
    # so disable ASR explicitly instead of assuming the package is absent.
    app = create_app({"TESTING": True, "LLM_MODE": "stub", "ASR_ENABLED": False})
    client = app.test_client()
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["asrReady"] is False
    # WS09-10: the public liveness surface no longer discloses provider
    # topology (mode/provider configuration moved to the admin detail view).
    assert "llmMode" not in body
    assert "providerConfigured" not in body


def test_health_asr_ready_reflects_probe(monkeypatch):
    from app.routes import health as health_route

    monkeypatch.setattr(health_route, "asr_ready", lambda cfg: True)
    app = create_app({"TESTING": True})
    r = app.test_client().get("/api/health")
    assert r.get_json()["asrReady"] is True

"""Phase 4b: AI Speaking roleplay (stub mode)."""


def test_roleplay_reply(client_with_seed):
    r = client_with_seed.post("/api/speaking/roleplay", json={
        "scenario": "Job interview",
        "history": [{"role": "assistant", "text": "Tell me about yourself."}],
        "userText": "I am a software engineer.",
    })
    assert r.status_code == 200
    b = r.get_json()
    assert "reply" in b and b["stub"] is True

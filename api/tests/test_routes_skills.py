"""Skill-route contracts for the current ARUORA application protocol."""


def body_has_questions(b):
    return "questions" in b


def test_writing_evaluate_stub(client_with_seed):
    r = client_with_seed.post(
        "/api/writing/evaluate",
        json={"taskType": "task2", "prompt": "p", "essay": "My essay text."},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert "bands" in body and "cefr" in body and body["stub"] is True
    # no key leak
    assert "OPENROUTER_API_KEY" not in body and "api_key" not in body


def test_speaking_evaluate_stub(client_with_seed):
    r = client_with_seed.post(
        "/api/speaking/evaluate",
        json={"part": "part2", "question": "Describe a book", "transcript": "I read..."},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert "bands" in body and body["stub"] is True


def test_reading_generate_starts_v12_practice_session(client_with_seed):
    r = client_with_seed.post(
        "/api/reading/generate",
        json={"band": "B2"},
    )

    assert r.status_code == 200
    body = r.get_json()

    assert body["skill"] == "reading"
    assert body["difficulty"] == "B2"
    assert body["scoringMethod"] == "practice-accuracy-v1"

    assert isinstance(body["practiceId"], str)
    assert body["practiceId"]

    assert body["questions"]

    # v1.2 must never leak grading material before submission.
    assert all(
        "answer" not in q and "explanation" not in q
        for q in body["questions"]
    )


def test_listening_generate_default_band(client_with_seed):
    r = client_with_seed.post(
        "/api/listening/generate",
        json={},
    )

    assert r.status_code == 200
    body = r.get_json()

    assert body_has_questions(body)
    assert body["skill"] == "listening"
    assert body["difficulty"] == "B1"
    assert body["scoringMethod"] == "practice-accuracy-v1"

    assert isinstance(body["practiceId"], str)
    assert body["practiceId"]

    assert all(
        "answer" not in q and "explanation" not in q
        for q in body["questions"]
    )


def test_speaking_transcribe_returns_text(client_with_seed, monkeypatch):
    import io

    from app.services import asr

    monkeypatch.setattr(
        asr,
        "transcribe",
        lambda audio, cfg, **k: {"transcript": "Hello world.", "language": "en",
                                "durationSec": 3.0, "model": "base", "asr": True,
                                "vad": True,
                                "segments": [{"start": 0.0, "end": 3.0,
                                              "avg_logprob": -0.2,
                                              "no_speech_prob": 0.05}]},
    )
    r = client_with_seed.post(
        "/api/speaking/transcribe",
        data={"audio": (io.BytesIO(b"fake-audio"), "speech.webm", "audio/webm")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["transcript"] == "Hello world."
    assert body["asr"] is True


def test_speaking_transcribe_requires_audio(client_with_seed):
    r = client_with_seed.post("/api/speaking/transcribe", data={},
                              content_type="multipart/form-data")
    assert r.status_code == 422
    assert r.get_json()["error"]["code"] == "VALIDATION"

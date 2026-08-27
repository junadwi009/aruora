"""
Batch 1 security remediation — LLM/ASR endpoint auth hardening (findings H1/M1/M2).

Verifies that the paid-LLM and compute-heavy ASR endpoints:
  - require an authenticated session (H1 roleplay, M1 transcribe), and
  - never do the paid/heavy work for an unauthenticated caller (M2 ordering),
  - cap oversized ASR uploads (M1), and
  - carry a tighter rate-limit rule for transcribe (M1).
"""
import io

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all


class RecordingGateway:
    """Stub gateway: records whether the model was invoked; returns benign data."""

    def __init__(self):
        self.score_called = False
        self.generate_called = False

    def score(self, task, **kw):
        self.score_called = True
        return {"bands": {"overall": 6.0}, "reply": "ok", "cefr": "B2"}

    def generate(self, task, **kw):
        self.generate_called = True
        return {"questions": []}


def _app(overrides=None):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    gw = RecordingGateway()
    o = {"TESTING": True, "SESSION_SECRET": "t", "REPO": Repository(Session), "GATEWAY": gw}
    o.update(overrides or {})
    return create_app(o), gw


def _authed(app):
    c = app.test_client()
    c.post("/api/account/register", json={"email": "a@b.com", "password": "correct horse battery staple"})
    return c


# ── H1: roleplay requires auth ────────────────────────────────────────────────

def test_roleplay_requires_auth():
    app, gw = _app()
    r = app.test_client().post(
        "/api/speaking/roleplay",
        json={"scenario": "x", "history": [], "userText": "hi"},
    )
    assert r.status_code == 401
    assert gw.score_called is False  # no paid call for an anonymous request


def test_roleplay_ok_when_signed_in():
    app, gw = _app()
    r = _authed(app).post(
        "/api/speaking/roleplay",
        json={"scenario": "x", "history": [], "userText": "hi"},
    )
    assert r.status_code == 200
    assert gw.score_called is True


# ── M1: transcribe requires auth ──────────────────────────────────────────────

def test_transcribe_requires_auth(monkeypatch):
    from app.services import asr
    monkeypatch.setattr(asr, "transcribe", lambda b, c, **k: {"transcript": "x", "asr": True, "durationSec": 5.0})
    app, _ = _app()
    r = app.test_client().post(
        "/api/speaking/transcribe",
        data={"audio": (io.BytesIO(b"x"), "a.webm")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 401


# ── M2: paid LLM is NOT invoked for an unauthenticated evaluate ───────────────

def test_writing_evaluate_no_llm_when_unauth(monkeypatch):
    from app.routes import writing
    monkeypatch.setattr(writing, "compute_metrics", lambda essay: {
        "wordCount": 1, "lexicalDiversity": {"mtld": 1.0},
        "readability": {"fleschKincaidGrade": 1.0}, "syntax": {"meanSentenceLength": 1.0},
    })
    app, gw = _app()
    r = app.test_client().post(
        "/api/writing/evaluate",
        json={"taskType": "task2", "prompt": "p", "essay": "hi"},
    )
    assert r.status_code == 401
    assert gw.score_called is False


def test_speaking_evaluate_no_llm_when_unauth():
    app, gw = _app()
    r = app.test_client().post(
        "/api/speaking/evaluate",
        json={"part": "part2", "question": "q", "transcript": "t"},
    )
    assert r.status_code == 401
    assert gw.score_called is False


# ── M1: transcribe caps oversized uploads ─────────────────────────────────────

def test_transcribe_rejects_oversize(monkeypatch):
    from app.services import asr
    monkeypatch.setattr(asr, "transcribe", lambda b, c, **k: {"transcript": "x", "asr": True, "durationSec": 5.0})
    app, _ = _app({"ASR_MAX_UPLOAD_BYTES": 16})
    c = _authed(app)
    r = c.post(
        "/api/speaking/transcribe",
        data={"audio": (io.BytesIO(b"x" * 100), "a.webm", "audio/webm")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 413


def test_transcribe_ok_within_cap(monkeypatch):
    from app.services import asr
    monkeypatch.setattr(asr, "transcribe", lambda b, c, **k: {"transcript": "hello", "asr": True, "durationSec": 5.0, "vad": True, "segments": [{"start": 0.0, "end": 5.0, "avg_logprob": -0.2, "no_speech_prob": 0.05}]})
    app, _ = _app({"ASR_MAX_UPLOAD_BYTES": 1024})
    c = _authed(app)
    r = c.post(
        "/api/speaking/transcribe",
        data={"audio": (io.BytesIO(b"x" * 10), "a.webm", "audio/webm")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    assert r.get_json()["transcript"] == "hello"


# ── M1: transcribe carries a tighter rate-limit rule ──────────────────────────

def test_transcribe_rate_rule():
    from app.ratelimit import rule_for
    rule = rule_for("/api/speaking/transcribe")
    assert (rule.limit, rule.window_sec) == (12, 60)

"""WS06 — Speaking, ASR, and audio evidence pipeline tests.

Covers: the audio feature contract (WS06-03), the quality gate (WS06-04),
queued ASR with 202+jobId and owner-scoped polling (WS06-02), ephemeral audio
retention (WS06-07), worker isolation config knobs (WS06-08), fail-closed
pronunciation (WS06-05), trusted audio-evidence attachment on evaluate
(WS06-06), and the text-estimate scope label (WS06-01).
"""
import io
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.errors import ApiError
from app.services import asr, audio_features, audio_store, pronunciation
from app.services.audio_store import AudioStore

STRONG = "correct horse battery staple"


class _FakeSegment:
    def __init__(self, text, start=None, end=None, avg_logprob=None, no_speech_prob=None):
        self.text = text
        self.start = start
        self.end = end
        self.avg_logprob = avg_logprob
        self.no_speech_prob = no_speech_prob


def _fake_asr(segments, duration=8.0, language="en"):
    """Monkeypatch asr.transcribe with a deterministic fake."""
    class _Info:
        pass

    def fake(audio_bytes, config, *, collect_segments=False):
        out = {
            "transcript": " ".join(s.text.strip() for s in segments).strip(),
            "language": language,
            "durationSec": duration,
            "model": "base",
            "asr": True,
        }
        if collect_segments:
            out["segments"] = [
                {"start": s.start, "end": s.end, "avg_logprob": s.avg_logprob,
                 "no_speech_prob": s.no_speech_prob}
                for s in segments
            ]
            out["vad"] = True
        return out

    return fake


def _make_app(**extra):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    repo = Repository(Session)
    o = {
        "TESTING": True,
        "SESSION_SECRET": "test-secret",
        "REPO": repo,
        "GATEWAY": Config and __import__("app.services.llm", fromlist=["LlmGateway"]).LlmGateway(Config({"LLM_MODE": "stub"})),
    }
    o.update(extra)
    return create_app(o), repo


def _auth(c):
    return c.post("/api/account/register",
                  json={"email": "speaker@example.com", "password": STRONG})


def _app(tmp_path, **extra):
    o = {"ASR_AUDIO_DIR": str(tmp_path / "audio"), "ASR_ENABLED": True}
    o.update(extra)
    return _make_app(**o)


# ── WS06-07: ephemeral audio store ───────────────────────────────────────────

def test_audio_store_roundtrip_and_delete(tmp_path):
    store = AudioStore(str(tmp_path), ttl_min=5)
    key = store.save(b"abc123")
    assert key and "/" not in key
    assert store.read(key) == b"abc123"
    store.delete(key)
    assert store.read(key) is None


def test_audio_store_rejects_path_traversal(tmp_path):
    store = AudioStore(str(tmp_path), ttl_min=5)
    assert store.read("../../etc/passwd") is None
    assert store.path("..\\windows") is None
    store.delete("../sneak")  # must not raise or delete anything outside


def test_audio_store_purges_expired(tmp_path):
    store = AudioStore(str(tmp_path), ttl_min=5)
    key = store.save(b"data")
    # Backdate the file beyond the TTL.
    p = store.path(key)
    old = time.time() - 6 * 60
    import os

    os.utime(p, (old, old))
    assert store.purge_expired() >= 1
    assert store.read(key) is None


# ── WS06-03: feature contract ────────────────────────────────────────────────

def test_feature_contract_shape_and_values():
    segments = [
        {"start": 0.0, "end": 5.0, "avg_logprob": -0.2, "no_speech_prob": 0.1},
        {"start": 6.5, "end": 10.0, "avg_logprob": -0.4, "no_speech_prob": 0.2},
    ]
    feats = audio_features.build_features(
        segments, {"duration": 10.5, "language": "en", "vad": True},
        "one two three four five six seven",
    )
    assert feats["duration_sec"] == 10.5
    assert feats["speech_sec"] == 10.0
    # one 1.5s gap → one pause, and it IS long (>= 1s)
    assert feats["pause_count"] == 1
    assert feats["long_pause_count"] == 1
    assert feats["mean_pause_ms"] == 1500.0
    assert feats["words_per_minute"] == round(7 / 10.0 * 60, 1) == 42.0
    assert 0 < feats["asr_confidence"] < 1
    assert feats["prosody"] is None and feats["alignment"] is None
    assert feats["quality"] == {"snr": None, "clipping": False, "vad": True}


def test_feature_contract_tolerates_missing_segments():
    feats = audio_features.build_features([], {"duration": None}, "")
    # VAD found no speech spans → honest zero, which the gate rejects.
    assert feats["speech_sec"] == 0.0
    assert feats["asr_confidence"] is None
    assert feats["pause_count"] == 0


# ── WS06-04: quality gate ────────────────────────────────────────────────────

def test_quality_gate_flags_near_silence():
    feats = audio_features.build_features([], {"duration": 4.0, "vad": True}, "")
    problems = audio_features.quality_check(feats, min_speech_sec=1.0)
    assert "near_silence" in problems


def test_quality_gate_flags_implausible_rate():
    feats = {"speech_sec": 5.0, "words_per_minute": 900.0,
             "quality": {"clipping": False}}
    assert "speech_rate_implausibly_high" in audio_features.quality_check(feats)


# ── WS06-02/04/07: queued transcribe route behaviour ─────────────────────────

def test_transcribe_queued_202_then_poll_result(tmp_path, monkeypatch):
    app, _ = _app(tmp_path, ASR_FORCE_QUEUE=True)
    monkeypatch.setattr(asr, "transcribe", _fake_asr([
        _FakeSegment(" Hello there ", 0.0, 3.0, -0.3, 0.1),
        _FakeSegment("world. ", 4.0, 6.0, -0.3, 0.1),
    ]))
    c = app.test_client()
    _auth(c)
    r = c.post("/api/speaking/transcribe",
               data={"audio": (io.BytesIO(b"fake"), "speech.webm", "audio/webm")},
               content_type="multipart/form-data")
    assert r.status_code == 202
    body = r.get_json()
    assert body["queued"] is True and body["jobId"]

    st = c.get(f"/api/jobs/{body['jobId']}")
    assert st.status_code == 200
    sbody = st.get_json()
    assert sbody["status"] == "succeeded"
    result = sbody["result"]
    assert result["transcript"] == "Hello there world."
    feats = result["features"]
    assert feats["speech_sec"] == 6.0
    assert feats["pause_count"] == 1
    # WS06-07: the raw audio object is gone after processing.
    store = audio_store.store_for_config(app.config["APP_CONFIG"])
    assert store.purge_expired() == 0 and not any((tmp_path / "audio").iterdir())


def test_transcribe_inline_returns_completed_result(tmp_path, monkeypatch):
    app, _ = _app(tmp_path)  # no REDIS_URL, no force → inline completion
    monkeypatch.setattr(asr, "transcribe", _fake_asr([
        _FakeSegment("Quick answer ", 0.0, 2.0, -0.2, 0.0),
    ]))
    c = app.test_client()
    _auth(c)
    r = c.post("/api/speaking/transcribe",
               data={"audio": (io.BytesIO(b"fake"), "speech.webm", "audio/webm")},
               content_type="multipart/form-data")
    assert r.status_code == 200
    body = r.get_json()
    assert body["transcript"] == "Quick answer"
    assert body["features"]["words_per_minute"] > 0


def test_transcribe_rejects_near_silence_as_insufficient_quality(tmp_path, monkeypatch):
    app, _ = _app(tmp_path)
    monkeypatch.setattr(asr, "transcribe", _fake_asr([], duration=4.0))
    c = app.test_client()
    _auth(c)
    r = c.post("/api/speaking/transcribe",
               data={"audio": (io.BytesIO(b"fake"), "speech.webm", "audio/webm")},
               content_type="multipart/form-data")
    assert r.status_code == 422
    assert r.get_json()["error"]["code"] == "INSUFFICIENT_AUDIO_QUALITY"


def test_transcribe_rejects_unsupported_mime(tmp_path):
    app, _ = _app(tmp_path)
    c = app.test_client()
    _auth(c)
    r = c.post("/api/speaking/transcribe",
               data={"audio": (io.BytesIO(b"fake"), "a.exe")},
               content_type="multipart/form-data")
    # werkzeug sniffs .exe as application/octet-stream → not on the allow-list
    assert r.status_code == 422
    assert r.get_json()["error"]["code"] == "VALIDATION"


def test_transcribe_rejects_over_duration(tmp_path, monkeypatch):
    app, _ = _app(tmp_path, ASR_MAX_DURATION_SEC=10)
    monkeypatch.setattr(asr, "transcribe", _fake_asr(
        [_FakeSegment("long", 0.0, 1.0)], duration=600.0))
    c = app.test_client()
    _auth(c)
    r = c.post("/api/speaking/transcribe",
               data={"audio": (io.BytesIO(b"fake"), "speech.webm", "audio/webm")},
               content_type="multipart/form-data")
    assert r.status_code == 413


def test_transcribe_audio_deleted_even_on_failure(tmp_path, monkeypatch):
    app, _ = _app(tmp_path)

    def _boom(audio, config, *, collect_segments=False):
        raise ApiError("ASR_UNAVAILABLE", "no model", 502)

    monkeypatch.setattr(asr, "transcribe", _boom)
    c = app.test_client()
    _auth(c)
    r = c.post("/api/speaking/transcribe",
               data={"audio": (io.BytesIO(b"fake"), "speech.webm", "audio/webm")},
               content_type="multipart/form-data")
    assert r.status_code == 502
    audio_dir = tmp_path / "audio"
    assert audio_dir.exists() is False or list(audio_dir.iterdir()) == []


# ── WS06-06: trusted acoustic evidence on evaluate ───────────────────────────

def test_evaluate_attaches_own_job_audio_features(tmp_path, monkeypatch):
    app, _ = _app(tmp_path, ASR_FORCE_QUEUE=True)
    monkeypatch.setattr(asr, "transcribe", _fake_asr([
        _FakeSegment("I enjoy reading books ", 0.0, 4.0, -0.2, 0.0),
    ]))
    c = app.test_client()
    _auth(c)
    job = c.post("/api/speaking/transcribe",
                 data={"audio": (io.BytesIO(b"fake"), "speech.webm", "audio/webm")},
                 content_type="multipart/form-data").get_json()
    r = c.post("/api/speaking/evaluate",
               json={"part": "part2", "question": "q", "transcript": "I enjoy reading books.",
                     "asrJobId": job["jobId"]})
    assert r.status_code == 200
    body = r.get_json()
    feats = body["metrics"]["audioFeatures"]
    assert feats["words_per_minute"] > 0
    # deterministic evidence stays distinct from the LLM judgment block
    assert "audioFeatures" not in (body["metrics"].get("llm") or {})


def test_evaluate_ignores_another_users_asr_job(tmp_path, monkeypatch):
    app, _ = _app(tmp_path, ASR_FORCE_QUEUE=True)
    monkeypatch.setattr(asr, "transcribe", _fake_asr([
        _FakeSegment("hello ", 0.0, 2.0, -0.2, 0.0),
    ]))
    c1 = app.test_client()
    _auth(c1)
    job = c1.post("/api/speaking/transcribe",
                  data={"audio": (io.BytesIO(b"fake"), "speech.webm", "audio/webm")},
                  content_type="multipart/form-data").get_json()
    # second user
    c1.post("/api/account/logout")
    c1.post("/api/account/register", json={"email": "two@example.com", "password": STRONG})
    r = c1.post("/api/speaking/evaluate",
                json={"part": "part2", "question": "q", "transcript": "hello there.",
                      "asrJobId": job["jobId"]})
    assert r.status_code == 200
    assert "audioFeatures" not in (r.get_json()["metrics"] or {})


# ── WS06-01: explicit estimate scope ─────────────────────────────────────────

def test_evaluate_labels_text_estimate_scope(client_with_seed):
    r = client_with_seed.post(
        "/api/speaking/evaluate",
        json={"part": "part2", "question": "q", "transcript": "I read many books today."},
    )
    body = r.get_json()
    assert body["estimateScope"] == "speaking_text_estimate"
    assert body["bands"]["pronunciation"] == "unassessed"


# ── WS06-05: pronunciation is validation-gated ───────────────────────────────

def test_pronunciation_estimator_off_by_default():
    cfg = Config({})
    assert pronunciation.estimator_available(cfg) is False
    with pytest.raises(ApiError) as ei:
        pronunciation.estimate({"duration_sec": 5.0}, "hello", cfg)
    assert ei.value.code == "ASR_UNAVAILABLE"


def test_pronunciation_estimator_requires_calibration_version():
    assert pronunciation.estimator_available(
        Config({"PRONUNCIATION_ESTIMATOR": "proto_v1"})) is False
    assert pronunciation.estimator_available(Config(
        {"PRONUNCIATION_ESTIMATOR": "proto_v1",
         "PRONUNCIATION_CALIBRATION_VERSION": "eval-2026-01"})) is True


# ── WS06-08: worker isolation knobs exist ────────────────────────────────────

def test_asr_worker_isolation_config_defaults():
    cfg = Config({})
    assert cfg.ASR_VAD is True
    assert cfg.ASR_MAX_DURATION_SEC == 300
    assert cfg.ASR_MIN_SPEECH_SEC == 1.0
    assert "audio/webm" in cfg.ASR_ALLOWED_MIME
    assert cfg.ASR_AUDIO_TTL_MIN == 30

"""
Tests for the Speaking ASR service (faster-whisper wrapper).

The real faster-whisper model is never loaded here — we inject a fake model so
the unit tests run offline and fast. The contract under test is the wrapper's
behaviour: shape of the returned dict, graceful failure, and the cheap
availability probe used by /api/health.
"""
import pytest

from app.config import Config
from app.errors import ApiError
from app.services import asr


class _FakeSegment:
    def __init__(self, text):
        self.text = text


class _FakeInfo:
    language = "en"
    duration = 7.5


class _FakeModel:
    """Mimics faster_whisper.WhisperModel.transcribe → (segments, info)."""

    def __init__(self, *a, **k):
        pass

    def transcribe(self, audio, **kw):
        return iter([_FakeSegment(" Hello "), _FakeSegment("world. ")]), _FakeInfo()


def test_transcribe_returns_joined_text(monkeypatch):
    monkeypatch.setattr(asr, "_get_model", lambda cfg: _FakeModel())
    out = asr.transcribe(b"fake-audio-bytes", Config({}))
    assert out["transcript"] == "Hello world."
    assert out["language"] == "en"
    assert out["durationSec"] == 7.5
    assert out["asr"] is True
    assert out["model"] == "base"


def test_transcribe_raises_when_model_unavailable(monkeypatch):
    def _boom(cfg):
        raise RuntimeError("faster_whisper not installed")

    monkeypatch.setattr(asr, "_get_model", _boom)
    with pytest.raises(ApiError) as ei:
        asr.transcribe(b"audio", Config({}))
    assert ei.value.code == "ASR_UNAVAILABLE"
    assert ei.value.status == 502


def test_transcribe_raises_when_disabled():
    with pytest.raises(ApiError) as ei:
        asr.transcribe(b"audio", Config({"ASR_ENABLED": False}))
    assert ei.value.code == "ASR_UNAVAILABLE"


def test_asr_ready_false_when_disabled():
    assert asr.asr_ready(Config({"ASR_ENABLED": False})) is False


def test_asr_ready_reflects_package_presence(monkeypatch):
    # Enabled + package present → ready
    monkeypatch.setattr(asr, "_package_available", lambda: True)
    assert asr.asr_ready(Config({"ASR_ENABLED": True})) is True
    # Enabled + package absent → not ready (no model load, just a probe)
    monkeypatch.setattr(asr, "_package_available", lambda: False)
    assert asr.asr_ready(Config({"ASR_ENABLED": True})) is False

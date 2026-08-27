"""
Speaking ASR via faster-whisper (fully local / offline).

`transcribe(audio_bytes, config)` decodes the uploaded audio and returns a
plain transcript dict. The WhisperModel is loaded ONCE per (model, device,
compute_type) as a process-level singleton on first use; the heavy import and
model files are baked into the api image (see api/Dockerfile) so inference
needs no network.

Mirrors the essay_metrics convention: degrade loudly but predictably — any
failure to load or run the model surfaces as `ApiError("ASR_UNAVAILABLE", 502)`
so the route can keep the typed-transcript fallback usable.

Return shape (camelCase):
{
  "transcript": str,
  "language": str | None,
  "durationSec": float,
  "model": str,
  "asr": True,
}
"""
from __future__ import annotations

import importlib.util
import io
import logging

from app.errors import ApiError

logger = logging.getLogger(__name__)

# Singleton model cache keyed by (model, device, compute_type).
_models: dict[tuple, object] = {}


def _package_available() -> bool:
    """Cheap probe: is faster_whisper importable? Does NOT load a model."""
    return importlib.util.find_spec("faster_whisper") is not None


def asr_ready(config) -> bool:
    """
    True when ASR is enabled in config AND the library is importable.
    Intentionally light (no model load) — safe to call from /api/health.
    """
    if not getattr(config, "ASR_ENABLED", True):
        return False
    return _package_available()


def _get_model(config):
    """
    Load (and cache) the WhisperModel for this config. Raises if the library or
    model is unavailable — the caller wraps that into an ApiError.
    """
    key = (config.ASR_MODEL, config.ASR_DEVICE, config.ASR_COMPUTE_TYPE)
    cached = _models.get(key)
    if cached is not None:
        return cached
    from faster_whisper import WhisperModel  # heavy import, deferred to first use

    model = WhisperModel(
        config.ASR_MODEL,
        device=config.ASR_DEVICE,
        compute_type=config.ASR_COMPUTE_TYPE,
    )
    _models[key] = model
    logger.info(
        "asr: WhisperModel loaded (model=%s device=%s compute=%s)",
        config.ASR_MODEL, config.ASR_DEVICE, config.ASR_COMPUTE_TYPE,
    )
    return model


def transcribe(audio_bytes: bytes, config, *, collect_segments: bool = False) -> dict:
    """
    Transcribe recorded speech audio to text.

    Parameters
    ----------
    audio_bytes : bytes
        Raw audio file bytes (webm/opus, wav, m4a, mp3 — decoded by PyAV).
    config : Config
        App config (ASR_ENABLED / ASR_MODEL / ASR_DEVICE / ASR_COMPUTE_TYPE).
    collect_segments : bool
        WS06-03: also return normalized segment timestamps/probabilities so
        the audio feature contract can be derived (worker path only).

    Returns
    -------
    dict
        Transcript payload (see module docstring); with ``segments`` when
        ``collect_segments`` is true.

    Raises
    ------
    ApiError("ASR_UNAVAILABLE", 502)
        If ASR is disabled, the model can't load, or decoding/transcription fails.
    ApiError("PAYLOAD_TOO_LARGE", 413)
        When the decoded audio exceeds ASR_MAX_DURATION_SEC (WS06-04).
    """
    if not getattr(config, "ASR_ENABLED", True):
        raise ApiError("ASR_UNAVAILABLE", "Speech transcription is disabled", 502)

    try:
        model = _get_model(config)
    except Exception as exc:  # noqa: BLE001
        logger.warning("asr: model unavailable — %s", exc)
        raise ApiError(
            "ASR_UNAVAILABLE",
            "Speech transcription is unavailable on this server",
            502,
        ) from exc

    # WS06-04: VAD keeps silence/non-speech out of the decode (quality gate
    # input, not a scoring feature). Resource-bounded decode via PyAV.
    vad = bool(getattr(config, "ASR_VAD", True))
    try:
        segments, info = model.transcribe(io.BytesIO(audio_bytes), beam_size=5,
                                          vad_filter=vad)
        text_parts: list[str] = []
        collected: list[dict] = []
        for s in segments:
            text_parts.append(s.text.strip())
            if collect_segments:
                collected.append({
                    "start": getattr(s, "start", None),
                    "end": getattr(s, "end", None),
                    "avg_logprob": getattr(s, "avg_logprob", None),
                    "no_speech_prob": getattr(s, "no_speech_prob", None),
                })
        text = " ".join(t for t in text_parts if t).strip()
    except ApiError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("asr: transcription failed — %s", exc)
        raise ApiError(
            "ASR_UNAVAILABLE",
            "Could not transcribe the audio (it may be empty or corrupt)",
            502,
        ) from exc

    duration = getattr(info, "duration", 0.0) or 0.0
    max_duration = float(getattr(config, "ASR_MAX_DURATION_SEC", 300))
    if duration > max_duration:
        # WS06-04: bounded worker time — reject over-long audio, never score it.
        raise ApiError(
            "PAYLOAD_TOO_LARGE",
            f"The recording is too long (max {int(max_duration)} seconds)",
            413,
        )

    out = {
        "transcript": text,
        "language": getattr(info, "language", None),
        "durationSec": round(float(duration), 2),
        "model": config.ASR_MODEL,
        "asr": True,
    }
    if collect_segments:
        out["segments"] = collected
        out["vad"] = vad
    return out

"""WS06-03/04/06 — provider-neutral audio feature contract + quality gate.

Deterministic, acoustic-only evidence extracted from the ASR run. This module
is the ONLY place audio metrics are derived, and it stays provider-neutral:
faster-whisper timestamps today, any forced-alignment/phoneme pipeline later.

The stored/broadcast shape matches the WS06-03 contract exactly (snake_case):

{
  "duration_sec": float,
  "speech_sec": float | None,
  "words_per_minute": float | None,
  "pause_count": int,
  "long_pause_count": int,
  "mean_pause_ms": float | None,
  "asr_confidence": float | None,      # null when the ASR provides no score
  "prosody": null,                     # reserved — no DSP pipeline yet, honest null
  "alignment": null,                   # reserved — no forced aligner yet
  "quality": {"snr": None, "clipping": False, "vad": bool}
}

Honesty rule: anything we cannot compute stays ``None``. No feature is
invented to keep the UI complete (same principle as pronunciation).

WS06-06: these metrics are DETERMINISTIC evidence. They must be stored
separately from any LLM judgment and never merged into model-facing prompt
payloads as authority.
"""
from __future__ import annotations

# Pause classification thresholds (ms) — long pauses are hesitation evidence.
PAUSE_LONG_MS = 1_000
# A "word" for rate purposes: whitespace-separated token (deterministic proxy).
_MIN_SPEECH_SEC_DEFAULT = 1.0
_MIN_WORDS_PER_SEC = 0.05   # <0.8 wpm sustained → almost certainly not speech
_MAX_WORDS_PER_SEC = 8.0    # >480 wpm → decode artifact, not a human


def build_features(segments: list[dict], info: dict, transcript: str) -> dict:
    """Build the WS06-03 contract from normalized segment dicts.

    ``segments``: [{"start": float|None, "end": float|None,
                    "avg_logprob": float|None, "no_speech_prob": float|None}]
    ``info``: {"duration": float|None, "language": str|None, "vad": bool}
    """
    duration = _f(info.get("duration"))

    spans = [(s.get("start"), s.get("end")) for s in segments]
    gaps_ms: list[float] = []
    prev_end: float | None = None
    for start, end in spans:
        s, e = _f(start), _f(end)
        if prev_end is not None and s is not None and s > prev_end:
            gaps_ms.append((s - prev_end) * 1000.0)
        if e is not None:
            prev_end = e if prev_end is None else max(prev_end, e)

    speech_sec = None
    ends = [e for _, e in spans if _f(e) is not None]
    starts = [s for s, _ in spans if _f(s) is not None]
    if not spans:
        # No speech spans at all (VAD removed everything): honest zero.
        speech_sec = 0.0
    elif ends:
        speech_sec = round(max(ends) - min(starts), 2) if starts else max(ends)
        speech_sec = max(0.0, speech_sec)

    words = len([w for w in (transcript or "").split() if w.strip()])
    wpm = None
    if speech_sec and speech_sec > 0 and words:
        wpm = round(words / speech_sec * 60.0, 1)

    logprobs = [_f(s.get("avg_logprob")) for s in segments]
    probs = [2.718281828 ** lp for lp in logprobs if lp is not None]
    asr_confidence = round(sum(probs) / len(probs), 3) if probs else None

    return {
        "duration_sec": round(duration, 2) if duration is not None else None,
        "speech_sec": speech_sec,
        "words_per_minute": wpm,
        "pause_count": len(gaps_ms),
        "long_pause_count": sum(1 for g in gaps_ms if g >= PAUSE_LONG_MS),
        "mean_pause_ms": round(sum(gaps_ms) / len(gaps_ms), 1) if gaps_ms else None,
        "asr_confidence": asr_confidence,
        "prosody": None,
        "alignment": None,
        "quality": {"snr": None, "clipping": False,
                    "vad": bool(info.get("vad", False))},
    }


def quality_check(features: dict, *, min_speech_sec: float = _MIN_SPEECH_SEC_DEFAULT) -> list[str]:
    """WS06-04 gate: return a list of problems ([] = acceptable audio).

    Returned BEFORE any scoring: "insufficient audio quality" must be the
    answer to bad audio, never a confident number derived from noise.
    """
    problems: list[str] = []
    speech = _f(features.get("speech_sec"))
    if speech is not None and speech < min_speech_sec:
        problems.append("near_silence")
    wpm = _f(features.get("words_per_minute"))
    if wpm is not None and speech and speech >= min_speech_sec:
        if wpm < _MIN_WORDS_PER_SEC * 60:
            problems.append("speech_rate_implausibly_low")
        elif wpm > _MAX_WORDS_PER_SEC * 60:
            problems.append("speech_rate_implausibly_high")
    if features.get("quality", {}).get("clipping"):
        problems.append("clipping_detected")
    return problems


def _f(v) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None

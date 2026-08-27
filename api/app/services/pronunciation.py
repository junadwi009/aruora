"""WS06-05 — pronunciation evidence is VALIDATION-GATED (fail closed).

Official IELTS assesses pronunciation on acoustic evidence a transcript does
not carry. Until a candidate feature/model pipeline has been validated against
consented, human-rated audio (agreement, subgroup error analysis, device
robustness, repeated-run stability — see 06 §WS06-05), NO pronunciation score
may leave this module. The default and the off-state are identical: nothing.

Validation contract before any estimator key is accepted:
1. a FROZEN evaluation pack (consented/licensed audio + human pronunciation
   criterion ratings) with a recorded version;
2. offline benchmark report: human-agreement statistics, accent/subgroup
   analysis (lawful, sample-size-backed), device/noise robustness,
   repeated-run stability;
3. a documented decision recorded against the pack version in config
   (``PRONUNCIATION_CALIBRATION_VERSION``).

Accent neutrality: the target construct is intelligibility and phonological
control — never "sounds native". Any candidate pipeline that correlates with
L1/accent rather than intelligibility fails validation by definition.
"""
from __future__ import annotations

from app.errors import ApiError


def estimator_available(cfg) -> bool:
    """True only when BOTH a validated estimator key and the calibration-pack
    version it was approved against are configured. Anything else = off."""
    return bool(
        getattr(cfg, "PRONUNCIATION_ESTIMATOR", "")
        and getattr(cfg, "PRONUNCIATION_CALIBRATION_VERSION", "")
    )


def estimate(audio_features: dict | None, transcript: str, cfg) -> dict:
    """Return a pronunciation evidence block, or raise UNAVAILABLE.

    This is the single choke point: no call site can produce a pronunciation
    score without passing through this gate. Until a validated pipeline is
    registered the answer is always ASR_UNAVAILABLE ("pronunciation could not
    be assessed"), which callers render as ``unassessed``.
    """
    if not estimator_available(cfg):
        raise ApiError(
            "ASR_UNAVAILABLE",
            "Pronunciation assessment is not available from this evidence",
            502,
        )
    # No validated estimator exists yet. When one does, it plugs in HERE —
    # behind the config gate above and its frozen calibration version — never
    # before it.
    raise ApiError(
        "ASR_UNAVAILABLE",
        "Pronunciation assessment is not available from this evidence",
        502,
    )

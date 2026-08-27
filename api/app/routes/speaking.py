"""
Speaking routes:
- POST /api/speaking/evaluate   — score a speaking attempt via the gateway.
- POST /api/speaking/roleplay — one AI partner turn in a conversation roleplay.
- POST /api/speaking/transcribe — transcribe recorded audio via local ASR.
"""
from flask import Blueprint, jsonify, request

from app.domain.scoring import normalize_speaking_estimate
from app.errors import ApiError
from app.routes._deps import _cfg, _gateway, _lang, _repo, _require_uid
from app.schemas import SpeakingEvaluateIn, SpeakingRoleplayIn
from app.services import asr
from app.validation import parse_body

bp = Blueprint("speaking", __name__)


@bp.post("/api/speaking/evaluate")
def speaking_evaluate():
    uid = _require_uid()  # gate BEFORE any paid LLM work
    body = parse_body(SpeakingEvaluateIn)

    # WS05-05: untrusted transcript ceiling before any paid call.
    max_transcript = _cfg().MAX_TRANSCRIPT_CHARS
    transcript = body.transcript
    if len(transcript) > max_transcript:
        raise ApiError("VALIDATION",
                       f"Transcript is too long (max {max_transcript} characters)", 422)

    gateway = _gateway()
    out = gateway.score(
        "speaking",
        lang=_lang(),
        part=body.part,
        question=body.question,
        transcript=transcript,
    )

    # WS02-04: fail closed — no pronunciation number may be presented from
    # transcript-only evidence; overall excludes the unassessable criterion.
    out = normalize_speaking_estimate(out)

    metrics = dict(out.get("metrics") or {})
    llm_meta = out.pop("_meta_llm", None)
    if llm_meta:
        metrics["llm"] = llm_meta
        out["metrics"] = metrics

    criteria_payload = {
        k: v for k, v in out.items()
        if k not in ("bands", "cefr", "metrics", "stub", "savedId", "score_metadata", "_meta_llm")
    }

    # Persist the attempt for the Progress tab (history + trends).
    out["savedId"] = _repo().save_attempt(
        uid,
        type="speaking",
        task=body.part or "",
        prompt=body.question or "",
        body=transcript,
        bands=out.get("bands", {}),
        cefr=out.get("cefr", ""),
        metrics=out.get("metrics", {}),
        criteria=criteria_payload,
        score_metadata=out.get("score_metadata"),
    )

    # WS21 — WML qualifying event, emitted only after persistence succeeded.
    from app.routes._analytics import emit
    emit("speaking_submitted", user_id=uid, part=body.part or "unknown")

    # gateway-defined shape; passthrough dict — shape validated client-side
    return jsonify(out), 200


@bp.post("/api/speaking/roleplay")
def speaking_roleplay():
    """One AI partner turn in a conversation roleplay."""
    _require_uid()  # authenticated only — this calls the paid LLM
    body = parse_body(SpeakingRoleplayIn)

    # WS05-05: cap the untrusted conversation context before the paid call.
    cfg = _cfg()
    history_turns = body.history[-12:]  # bound context, newest kept
    if len(body.user_text) > cfg.MAX_ROLEPLAY_TURN_CHARS:
        raise ApiError("VALIDATION",
                       f"Utterance is too long (max {cfg.MAX_ROLEPLAY_TURN_CHARS})", 422)
    if len(body.scenario) > cfg.MAX_SCENARIO_CHARS:
        raise ApiError("VALIDATION",
                       f"Scenario is too long (max {cfg.MAX_SCENARIO_CHARS})", 422)

    history = "\n".join(
        f"{t.role or '?'}: {t.text[:cfg.MAX_ROLEPLAY_TURN_CHARS]}"
        for t in history_turns
    )
    out = _gateway().score(
        "roleplay",
        scenario=body.scenario,
        history=history or "(start)",
        userText=body.user_text,
    )
    return jsonify(out), 200


@bp.post("/api/speaking/transcribe")
def speaking_transcribe():
    """Accept a multipart audio upload and return a transcript dict."""
    _require_uid()  # authenticated only — ASR is CPU-heavy (cost/DoS guard)
    cfg = _cfg()
    f = request.files.get("audio")
    if f is None:
        raise ApiError("VALIDATION", "An 'audio' file is required", 422)
    audio_bytes = f.read()
    if not audio_bytes:
        raise ApiError("VALIDATION", "The uploaded audio is empty", 422)
    # ASR-specific inner cap (tighter than the global MAX_CONTENT_LENGTH) so a
    # single request can't tie up the CPU with a huge decode.
    if len(audio_bytes) > cfg.ASR_MAX_UPLOAD_BYTES:
        raise ApiError("PAYLOAD_TOO_LARGE", "The audio file is too large", 413)
    out = asr.transcribe(audio_bytes, cfg)
    return jsonify(out), 200

"""
Speaking routes:
- POST /api/speaking/evaluate   — score a speaking attempt via the gateway.
- POST /api/speaking/roleplay — one AI partner turn in a conversation roleplay.
- POST /api/speaking/transcribe — queued ASR: 202 + jobId (poll /api/jobs/<id>),
  or the completed transcript directly when the eager dispatcher finished
  in-request (offline dev topology).
"""
from flask import Blueprint, current_app, jsonify, request

from app.domain.scoring import normalize_speaking_estimate
from app.errors import ApiError
from app.routes._deps import _cfg, _gateway, _lang, _repo, _require_uid
from app.schemas import SpeakingEvaluateIn, SpeakingRoleplayIn
from app.services import asr
from app.validation import parse_body

bp = Blueprint("speaking", __name__)

# Job error code → HTTP status for the synchronous (inline) response path.
_JOB_ERROR_STATUS = {
    "VALIDATION": 422,
    "INSUFFICIENT_AUDIO_QUALITY": 422,
    "PAYLOAD_TOO_LARGE": 413,
    "ASR_UNAVAILABLE": 502,
    "INTERNAL_JOB_ERROR": 502,
}


def _trusted_audio_features(job_id: str | None, uid: int) -> dict | None:
    """WS06-06: attach DETERMINISTIC audio evidence to an attempt, taken only
    from the user's own completed ASR job (never from client-supplied values —
    job results are computed server-side)."""
    if not job_id:
        return None
    jobs = current_app.config.get("JOBS")
    if jobs is None:
        return None
    st = jobs.get_status(job_id, uid)  # owner-scoped: other users' jobs → None
    if not st or st.get("status") != "succeeded" or st.get("type") != "transcribe":
        return None
    return (st.get("result") or {}).get("features")


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

    # WS06-06: acoustic evidence from the user's own ASR job (server-computed,
    # owner-scoped). Stored under metrics.audioFeatures — always distinct from
    # the LLM judgment block (metrics.llm).
    audio_features = _trusted_audio_features(body.asrJobId, uid)
    if audio_features:
        out["metrics"]["audioFeatures"] = audio_features

    # Label the estimate scope explicitly (WS06-01): this result is derived
    # from TEXT evidence; pronunciation is unassessed, not scored.
    out["estimateScope"] = "speaking_text_estimate"

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
    """WS06-02 — queued ASR.

    The web process NEVER decodes audio: the upload is validated, stored as a
    short-lived private object (WS06-07) and enqueued on the dedicated ``asr``
    queue. The browser gets ``202 {jobId}`` and polls ``GET /api/jobs/<id>``
    (owner-scoped). When the eager dispatcher finished within this request
    (offline dev topology), the completed transcript is returned directly for
    compatibility.
    """
    uid = _require_uid()  # authenticated only — ASR is CPU-heavy (cost/DoS guard)
    cfg = _cfg()
    jobs = current_app.config.get("JOBS")
    if jobs is None:
        raise ApiError("UNAVAILABLE", "Speech transcription is not available", 503)

    f = request.files.get("audio")
    if f is None:
        raise ApiError("VALIDATION", "An 'audio' file is required", 422)
    audio_bytes = f.read()
    if not audio_bytes:
        raise ApiError("VALIDATION", "The uploaded audio is empty", 422)
    # WS06-04 inner cap (tighter than MAX_CONTENT_LENGTH): a single upload can
    # never tie up the queue with a huge decode.
    if len(audio_bytes) > cfg.ASR_MAX_UPLOAD_BYTES:
        raise ApiError("PAYLOAD_TOO_LARGE", "The audio file is too large", 413)
    # WS06-04 MIME/container gate.
    mime = (f.mimetype or "").split(";")[0].strip().lower()
    allowed = {m.split(";")[0].strip().lower() for m in cfg.ASR_ALLOWED_MIME}
    if mime and mime not in allowed:
        raise ApiError("VALIDATION",
                       "Unsupported audio format — use webm, wav, mp3 or m4a", 422)

    from app.services.audio_store import store_for_config

    store = store_for_config(cfg)
    key = store.save(audio_bytes)
    try:
        job, _created = jobs.enqueue(
            "transcribe", queue="asr",
            payload={"audioKey": key, "mime": mime}, user_id=uid,
        )
    except Exception:
        store.delete(key)  # no orphaned audio when the queue rejects us
        raise

    queued_response = cfg.ASR_FORCE_QUEUE or jobs.mode == "queued"
    if not queued_response:
        # Eager dispatcher finished in-request: surface the terminal state now.
        st = jobs.get_status(job["id"], uid)
        status = (st or {}).get("status")
        if status == "succeeded":
            result = dict(st.get("result") or {})
            result["jobId"] = job["id"]
            return jsonify(result), 200
        if status in ("failed", "cancelled"):
            code = (st or {}).get("errorCode") or "ASR_UNAVAILABLE"
            message = (st or {}).get("errorMessage") or "Transcription failed"
            raise ApiError(code, message, _JOB_ERROR_STATUS.get(code, 502))
    return jsonify({"jobId": job["id"], "status": "queued", "queued": True}), 202

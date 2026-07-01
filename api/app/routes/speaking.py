"""
Speaking routes:
- POST /api/speaking/evaluate   — score a speaking attempt via the gateway.
- POST /api/speaking/transcribe — transcribe recorded audio via local ASR.
"""
from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _cfg, _gateway, _lang, _repo, _require_uid
from app.services import asr

bp = Blueprint("speaking", __name__)


@bp.post("/api/speaking/evaluate")
def speaking_evaluate():
    body = request.get_json(force=True) or {}
    gateway = _gateway()
    out = gateway.score(
        "speaking",
        lang=_lang(),
        part=body.get("part"),
        question=body.get("question"),
        transcript=body.get("transcript", ""),
    )

    # Persist the attempt for the Progress tab (history + trends).
    out["savedId"] = _repo().save_attempt(
        _require_uid(),
        type="speaking",
        task=body.get("part", ""),
        prompt=body.get("question", ""),
        body=body.get("transcript", ""),
        bands=out.get("bands", {}),
        cefr=out.get("cefr", ""),
        metrics=out.get("metrics", {}),
        criteria={
            k: v for k, v in out.items()
            if k not in ("bands", "cefr", "metrics", "stub", "savedId")
        },
    )

    # gateway-defined shape; passthrough dict — shape validated client-side
    return jsonify(out), 200


@bp.post("/api/speaking/roleplay")
def speaking_roleplay():
    """One AI partner turn in a conversation roleplay."""
    body = request.get_json(force=True) or {}
    history = "\n".join(f"{t.get('role')}: {t.get('text')}" for t in body.get("history", []))
    out = _gateway().score(
        "roleplay",
        scenario=body.get("scenario", "casual conversation"),
        history=history or "(start)",
        userText=body.get("userText", ""),
    )
    return jsonify(out), 200


@bp.post("/api/speaking/transcribe")
def speaking_transcribe():
    """Accept a multipart audio upload and return a transcript dict."""
    f = request.files.get("audio")
    if f is None:
        raise ApiError("VALIDATION", "An 'audio' file is required", 422)
    audio_bytes = f.read()
    if not audio_bytes:
        raise ApiError("VALIDATION", "The uploaded audio is empty", 422)
    out = asr.transcribe(audio_bytes, _cfg())
    return jsonify(out), 200

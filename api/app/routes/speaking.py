"""
Speaking routes:
- POST /api/speaking/evaluate   — score a speaking attempt via the gateway.
- POST /api/speaking/transcribe — transcribe recorded audio via local ASR.
"""
from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _cfg, _gateway
from app.services import asr

bp = Blueprint("speaking", __name__)


@bp.post("/api/speaking/evaluate")
def speaking_evaluate():
    body = request.get_json(force=True) or {}
    gateway = _gateway()
    out = gateway.score(
        "speaking",
        part=body.get("part"),
        question=body.get("question"),
        transcript=body.get("transcript", ""),
    )
    # gateway-defined shape; passthrough dict — shape validated client-side
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

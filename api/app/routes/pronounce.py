"""
Phase 2d-3 — pronunciation read-aloud drill.

- POST /api/pronounce/sentence {level?,topic?} → a read-aloud target {text,focus,tips[]}
- POST /api/pronounce/feedback {target,transcript,accuracy,missed[]} → {summary,wordTips[],prosody[]}

Scoring is approximate (browser recogniser word-match + LLM tips), not phoneme-level.
"""
from flask import Blueprint, jsonify

from app.errors import ApiError
from app.routes._deps import _cfg, _gateway, _lang, _repo, _require_uid
from app.routes._gencap import GEN_CAP_CODE
from app.schemas import PronounceFeedbackIn, PronounceSentenceIn
from app.services.ai_usage import note_custom_generation, require_custom_generation
from app.validation import parse_body

bp = Blueprint("pronounce", __name__)


@bp.post("/api/pronounce/sentence")
def pronounce_sentence():
    uid = _require_uid()  # authenticated only — this calls the paid LLM
    b = parse_body(PronounceSentenceIn)
    topic = b.topic or ""
    if len(topic) > _cfg().MAX_TOPIC_CHARS:
        raise ApiError("VALIDATION",
                       f"Topic is too long (max {_cfg().MAX_TOPIC_CHARS} characters)", 422)
    require_custom_generation(uid, _repo(), _cfg())
    out = _gateway().generate("generate", skill="pronounce", band=b.level or "B1",
                              topic=topic or None)
    note_custom_generation(uid, _repo())
    return jsonify(out), 200


@bp.post("/api/pronounce/feedback")
def pronounce_feedback():
    _require_uid()  # authenticated only — this calls the paid LLM
    b = parse_body(PronounceFeedbackIn)
    cfg = _cfg()
    if len(b.transcript) > cfg.MAX_TRANSCRIPT_CHARS:
        raise ApiError("VALIDATION",
                       f"Transcript is too long (max {cfg.MAX_TRANSCRIPT_CHARS})", 422)
    out = _gateway().score(
        "pronounce",
        lang=_lang(),
        target=b.target,
        transcript=b.transcript,
        accuracy=b.accuracy,
        missed=", ".join(b.missed)[:400] or "none",
    )
    return jsonify(out), 200

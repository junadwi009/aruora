"""
Phase 2d-3 — pronunciation read-aloud drill.

- POST /api/pronounce/sentence {level?,topic?} → a read-aloud target {text,focus,tips[]}
- POST /api/pronounce/feedback {target,transcript,accuracy,missed[]} → {summary,wordTips[],prosody[]}

Scoring is approximate (browser recogniser word-match + LLM tips), not phoneme-level.
"""
from flask import Blueprint, jsonify, request

from app.routes._deps import _gateway

bp = Blueprint("pronounce", __name__)


@bp.post("/api/pronounce/sentence")
def pronounce_sentence():
    b = request.get_json(force=True) or {}
    out = _gateway().generate("generate", skill="pronounce", band=b.get("level", "B1"),
                              topic=b.get("topic"))
    return jsonify(out), 200


@bp.post("/api/pronounce/feedback")
def pronounce_feedback():
    b = request.get_json(force=True) or {}
    out = _gateway().score(
        "pronounce",
        target=b.get("target", ""),
        transcript=b.get("transcript", ""),
        accuracy=b.get("accuracy", 0),
        missed=", ".join(b.get("missed", [])) or "none",
    )
    return jsonify(out), 200

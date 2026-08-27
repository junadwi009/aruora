"""Phase 2d-4 — topic vocabulary generation.

WS27 Stage E: the per-topic fresh generation is an explicitly learner-owned
CUSTOM generation — metered via the policy service (app.services.ai_usage),
never via raw provider accounting. It is NOT a pool serve.
"""
from flask import Blueprint, jsonify

from app.routes._deps import _cfg, _gateway, _repo, _require_uid
from app.schemas import VocabIn
from app.services.ai_usage import note_custom_generation, require_custom_generation
from app.validation import parse_body

bp = Blueprint("vocab", __name__)


@bp.post("/api/vocab")
def vocab():
    uid = _require_uid()  # authenticated only — this calls the paid LLM
    b = parse_body(VocabIn)
    require_custom_generation(uid, _repo(), _cfg())
    out = _gateway().generate(
        "generate", skill="vocab", band=b.level or "B1", topic=b.topic or "general"
    )
    note_custom_generation(uid, _repo())
    from app.routes._gencap import public_result
    return jsonify(public_result(out)), 200

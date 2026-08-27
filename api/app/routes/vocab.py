"""Phase 2d-4 — topic vocabulary generation."""
from flask import Blueprint, jsonify

from app.errors import ApiError
from app.routes._deps import _cfg, _gateway, _repo, _require_uid
from app.routes._gencap import cap_reached, note_generation, GEN_CAP_CODE
from app.schemas import VocabIn
from app.validation import parse_body

bp = Blueprint("vocab", __name__)


@bp.post("/api/vocab")
def vocab():
    uid = _require_uid()  # authenticated only — this calls the paid LLM
    b = parse_body(VocabIn)
    if cap_reached(uid, _repo(), _cfg()):
        raise ApiError(GEN_CAP_CODE, "Daily generation limit reached", 429)
    out = _gateway().generate(
        "generate", skill="vocab", band=b.level or "B1", topic=b.topic or "general"
    )
    note_generation(uid, _repo())
    from app.routes._gencap import public_result
    return jsonify(public_result(out)), 200

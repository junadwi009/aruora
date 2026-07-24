"""Phase 2d-4 — topic vocabulary generation."""
from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _cfg, _gateway, _repo, _require_uid
from app.routes._gencap import cap_reached, note_generation

bp = Blueprint("vocab", __name__)


@bp.post("/api/vocab")
def vocab():
    uid = _require_uid()  # authenticated only — this calls the paid LLM
    b = request.get_json(force=True) or {}
    if cap_reached(uid, _repo(), _cfg()):
        raise ApiError("GEN_CAP_REACHED", "Daily generation limit reached", 429)
    out = _gateway().generate(
        "generate", skill="vocab", band=b.get("level", "B1"), topic=b.get("topic", "general")
    )
    note_generation(uid, _repo())
    return jsonify(out), 200

"""Phase 2d-4 — topic vocabulary generation."""
from flask import Blueprint, jsonify, request

from app.routes._deps import _gateway, _require_uid

bp = Blueprint("vocab", __name__)


@bp.post("/api/vocab")
def vocab():
    _require_uid()  # authenticated only — this calls the paid LLM
    b = request.get_json(force=True) or {}
    out = _gateway().generate(
        "generate", skill="vocab", band=b.get("level", "B1"), topic=b.get("topic", "general")
    )
    return jsonify(out), 200

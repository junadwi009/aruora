"""Phase 2d-4 — topic vocabulary generation."""
from flask import Blueprint, jsonify, request

from app.routes._deps import _gateway

bp = Blueprint("vocab", __name__)


@bp.post("/api/vocab")
def vocab():
    b = request.get_json(force=True) or {}
    out = _gateway().generate(
        "generate", skill="vocab", band=b.get("level", "B1"), topic=b.get("topic", "general")
    )
    return jsonify(out), 200

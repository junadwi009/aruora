"""
POST /api/listening/generate — generate a listening transcript + questions via the gateway.
"""
from flask import Blueprint, jsonify, request

from app.routes._deps import _gateway, _require_uid

bp = Blueprint("listening", __name__)


@bp.post("/api/listening/generate")
def listening_generate():
    _require_uid()  # authenticated only — this calls the paid LLM
    body = request.get_json(force=True) or {}
    band = body.get("band", "B1")
    gateway = _gateway()
    out = gateway.generate("generate", skill="listening", band=band)
    # gateway-defined shape; passthrough dict — shape validated client-side
    return jsonify(out), 200

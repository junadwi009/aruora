"""
POST /api/listening/generate — serve a listening set. Efficiency policy is the
shared app.routes._gencap.serve_or_generate (see reading.py).
"""
from flask import Blueprint, jsonify, request

from app.routes._deps import _cfg, _gateway, _repo, _require_uid
from app.routes._gencap import serve_or_generate

bp = Blueprint("listening", __name__)


@bp.post("/api/listening/generate")
def listening_generate():
    uid = _require_uid()
    body = request.get_json(force=True) or {}
    out = serve_or_generate("listening", "B1", uid, _repo(), _cfg(), _gateway(), body)
    return jsonify(out), 200

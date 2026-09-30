"""
POST /api/listening/generate

Compatibility entry point for starting a server-owned Listening practice session.
The returned payload is backed by the v1.2 practice-session protocol.
"""
from flask import Blueprint, jsonify

from app.routes._deps import _cfg, _gateway, _jobs, _repo, _require_uid
from app.routes._gencap import serve_or_generate
from app.schemas import BandGenerateIn
from app.validation import parse_body

bp = Blueprint("listening", __name__)


@bp.post("/api/listening/generate")
def listening_generate():
    from app.routes.practice import start_for
    body = parse_body(BandGenerateIn)
    return jsonify(start_for("listening", body.band or "B1")), 200

"""
POST /api/reading/generate

Compatibility entry point for starting a server-owned Reading practice session.
The returned payload contains a practiceId and public question snapshot without
answer keys. Scoring is performed server-side through the v1.2 practice protocol.
"""
from flask import Blueprint, jsonify

from app.schemas import BandGenerateIn
from app.validation import parse_body

bp = Blueprint("reading", __name__)


@bp.post("/api/reading/generate")
def reading_generate():
    from app.routes.practice import start_for
    body = parse_body(BandGenerateIn)
    return jsonify(start_for("reading", body.band or "B1")), 200

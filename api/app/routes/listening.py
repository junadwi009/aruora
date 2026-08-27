"""
POST /api/listening/generate — serve a listening set. Efficiency policy is the
shared app.routes._gencap.serve_or_generate (see reading.py).
"""
from flask import Blueprint, jsonify

from app.routes._deps import _cfg, _gateway, _jobs, _repo, _require_uid
from app.routes._gencap import serve_or_generate
from app.schemas import BandGenerateIn
from app.validation import parse_body

bp = Blueprint("listening", __name__)


@bp.post("/api/listening/generate")
def listening_generate():
    uid = _require_uid()
    body = parse_body(BandGenerateIn)
    out = serve_or_generate("listening", "B1", uid, _repo(), _cfg(), _gateway(),
                            {"band": body.band} if body.band is not None else {},
                            jobs=_jobs())
    return jsonify(out), 200

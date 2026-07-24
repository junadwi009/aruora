"""
POST /api/reading/generate — serve a reading set.

Efficiency (Feature B) is in app.routes._gencap.serve_or_generate: once
POOL_TARGET sets exist for (reading, band) the pool is frozen and a random
stored set is served (no LLM); below target and under the daily cap we
generate + grow the pool; when capped we fall back to the pool or 429.
"""
from flask import Blueprint, jsonify, request

from app.routes._deps import _cfg, _gateway, _repo, _require_uid
from app.routes._gencap import serve_or_generate

bp = Blueprint("reading", __name__)


@bp.post("/api/reading/generate")
def reading_generate():
    uid = _require_uid()
    body = request.get_json(force=True) or {}
    out = serve_or_generate("reading", "B2", uid, _repo(), _cfg(), _gateway(), body)
    return jsonify(out), 200

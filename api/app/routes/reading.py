"""
POST /api/reading/generate — serve a reading set.

Efficiency (Feature B) is in app.routes._gencap.serve_or_generate: once
POOL_TARGET sets exist for (reading, band) the pool is frozen and a random
stored set is served (no LLM); below target and under the daily cap we
generate + grow the pool; when capped we fall back to the pool or 429.
"""
from flask import Blueprint, jsonify

from app.routes._deps import _cfg, _gateway, _jobs, _repo, _require_uid
from app.routes._gencap import serve_or_generate
from app.schemas import BandGenerateIn
from app.validation import parse_body

bp = Blueprint("reading", __name__)


@bp.post("/api/reading/generate")
def reading_generate():
    uid = _require_uid()
    body = parse_body(BandGenerateIn)
    out = serve_or_generate("reading", "B2", uid, _repo(), _cfg(), _gateway(),
                            {"band": body.band} if body.band is not None else {},
                            jobs=_jobs())
    return jsonify(out), 200

"""GET /api/jobs/<job_id> — owner-only job status (WS07-03).

Job IDs are unguessable UUIDs AND the lookup is scoped to the session user:
another user's job — and every system job — simply does not exist here.
Responses carry only safe fields: status/progress/error-code; never payloads,
provider output, or internal metadata.
"""
from flask import Blueprint, current_app, jsonify, request

from app.errors import ApiError
from app.routes._deps import _require_uid

bp = Blueprint("jobs", __name__)


@bp.get("/api/jobs/<job_id>")
def job_status(job_id: str):
    uid = _require_uid()
    jobs = current_app.config.get("JOBS")
    if jobs is None:
        raise ApiError("UNAVAILABLE", "Job tracking is not available", 503)
    out = jobs.get_status(job_id, uid)
    if out is None:
        raise ApiError("NOT_FOUND", "Job not found", 404)
    return jsonify(out), 200


@bp.get("/api/jobs/lookup")
def job_lookup():
    import re
    uid = _require_uid()
    kind, key = request.args.get("type", ""), request.args.get("key", "")
    if kind not in ("score_writing", "score_speaking") or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", key):
        raise ApiError("VALIDATION", "Invalid evaluation reference", 422)
    repo = current_app.config["REPO"]
    job = repo.job_by_idempotency(uid, f"{kind}:u:{uid}:{key}")
    if job is None:
        raise ApiError("NOT_FOUND", "Evaluation request not found", 404)
    return jsonify(current_app.config["JOBS"].get_status(job["id"], uid)), 200

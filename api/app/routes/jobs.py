"""GET /api/jobs/<job_id> — owner-only job status (WS07-03).

Job IDs are unguessable UUIDs AND the lookup is scoped to the session user:
another user's job — and every system job — simply does not exist here.
Responses carry only safe fields: status/progress/error-code; never payloads,
provider output, or internal metadata.
"""
from flask import Blueprint, current_app, jsonify

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

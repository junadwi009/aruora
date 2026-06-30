"""
Phase 2c — read-only history & trends for the Progress tab.

- GET /api/history/attempts?type=writing|speaking → newest-first summaries
- GET /api/history/attempt/<id>                    → full re-renderable payload
- GET /api/stats/trends                            → per-skill band time series
"""
from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _repo, _uid

bp = Blueprint("history", __name__)


@bp.get("/api/history/attempts")
def history_attempts():
    uid = _uid()
    if uid is None:
        return jsonify([]), 200
    return jsonify(_repo().list_attempts(uid, request.args.get("type"))), 200


@bp.get("/api/history/attempt/<int:attempt_id>")
def history_attempt(attempt_id):
    uid = _uid()
    attempt = _repo().get_attempt(uid, attempt_id) if uid is not None else None
    if attempt is None:
        raise ApiError("NOT_FOUND", "Attempt not found", 404)
    return jsonify(attempt), 200


@bp.get("/api/stats/trends")
def stats_trends():
    uid = _uid()
    if uid is None:
        return jsonify({"writing": [], "speaking": [], "reading": [], "listening": []}), 200
    return jsonify(_repo().trends(uid)), 200


@bp.get("/api/stats/activity")
def stats_activity():
    from datetime import datetime, timezone
    uid = _uid()
    if uid is None:
        return jsonify({"current": 0, "longest": 0, "today": 0, "daysActive": 0}), 200
    return jsonify(_repo().activity_stats(uid, datetime.now(timezone.utc).date())), 200

"""
Phase 2c — read-only history & trends for the Progress tab.

- GET /api/history/attempts?type=writing|speaking → newest-first summaries
- GET /api/history/attempt/<id>                    → full re-renderable payload
- GET /api/stats/trends                            → per-skill band time series
"""
from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _repo

bp = Blueprint("history", __name__)


@bp.get("/api/history/attempts")
def history_attempts():
    return jsonify(_repo().list_attempts(request.args.get("type"))), 200


@bp.get("/api/history/attempt/<int:attempt_id>")
def history_attempt(attempt_id):
    attempt = _repo().get_attempt(attempt_id)
    if attempt is None:
        raise ApiError("NOT_FOUND", "Attempt not found", 404)
    return jsonify(attempt), 200


@bp.get("/api/stats/trends")
def stats_trends():
    return jsonify(_repo().trends()), 200

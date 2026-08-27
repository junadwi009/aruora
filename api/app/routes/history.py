"""
Phase 2c — read-only history & trends for the Progress tab.

- GET /api/history/attempts?type=writing|speaking → newest-first summaries
- GET /api/history/attempt/<id>                    → full re-renderable payload
- GET /api/history/readiness                       → WS20 readiness contract
- GET /api/stats/trends                            → per-skill band time series
"""
from flask import Blueprint, jsonify, request

from app.domain.readiness import build_readiness
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


@bp.get("/api/history/readiness")
def history_readiness():
    """WS20 readiness contract — deterministic estimate/gap/priority summary.

    Never a percentage, never an official result. Skill targets are taken from
    the profile ONLY when numeric (CEFR-string targets are not band numbers).
    """
    uid = _uid()
    if uid is None:
        raise ApiError("UNAUTHORIZED", "Sign in to continue", 401)
    repo = _repo()
    user = repo.get_user_by_id(uid)
    if user is None:
        raise ApiError("NOT_FOUND", "no user profile", 404)

    raw_targets = user.skill_targets or {}
    numeric_targets = {
        k: float(v) for k, v in raw_targets.items()
        if isinstance(v, (int, float))
    }
    return jsonify(build_readiness(
        repo.latest_skill_estimates(uid),
        target_band=float(user.target_band),
        skill_targets=numeric_targets or None,
    )), 200


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

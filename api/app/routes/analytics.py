"""WS21 — analytics beacon + admin summary endpoints.

- POST /api/analytics/events : client beacons, restricted to
  CLIENT_EMITTABLE allow-list (completions can never be client-declared).
- GET  /api/admin/analytics/summary : admin-only. WML + per-event counts +
  per-cohort breakdown with lecturer_uat_* rows kept SEPARATE from voluntary
  cohorts (never one merged retention number).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _repo
from app.routes._analytics import emit_client_beacon

bp = Blueprint("analytics", __name__)


@bp.post("/api/analytics/events")
def analytics_beacon():
    body = request.get_json(force=True) or {}
    event_name = str(body.get("event") or "")
    accepted = emit_client_beacon(
        event_name,
        body if isinstance(body, dict) else {},
        anonymous_id=(str(body.get("anonymousId"))[:64]
                      if body.get("anonymousId") else None),
    )
    if not accepted:
        # Fail closed for fabricated/unknown events — but cheaply, and never
        # with detail that helps attackers probe the taxonomy.
        raise ApiError("VALIDATION", "Event not accepted", 422)
    return jsonify({"ok": True}), 200


@bp.get("/api/admin/analytics/summary")
def analytics_summary():
    from app.routes.admin import _require_admin
    _require_admin()

    repo = _repo()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    counts = repo.analytics_counts()
    summary = {
        "wml": {
            "windowDays": 7,
            "count": repo.weekly_meaningful_learners(as_of=now),
        },
        "eventCounts": counts,
        "cohorts": repo.analytics_by_cohort(),
        "generatedAt": now.isoformat(),
        "since": week_ago.isoformat(),
    }
    return jsonify(summary), 200

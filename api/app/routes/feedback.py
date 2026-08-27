"""
Test-phase feedback gate (Feature A).

Each user accumulates focused in-app time via /api/gate/heartbeat. At
GATE_LOCK_SECONDS the app locks until the user submits a rating + insight
(/api/gate/unlock), which is stored and emailed to the admin. One-time:
once unlocked, never locks again. Admins are exempt.
"""
from flask import Blueprint, jsonify

from app.errors import ApiError
from app.routes._deps import _cfg, _repo, _require_uid
from app.routes.admin import _is_admin_email, _require_admin
from app.schemas import GateHeartbeatIn, GateUnlockIn
from app.services import mailer
from app.validation import parse_body

bp = Blueprint("gate", __name__)

MIN_INSIGHT = 20


def _is_admin_uid(uid) -> bool:
    u = _repo().get_user_by_id(uid) if uid else None
    return bool(u and _is_admin_email(u.email))


def _locked(cfg, gate: dict, is_admin: bool) -> bool:
    return (
        cfg.GATE_ENABLED
        and not is_admin
        and gate["unlocked_at"] is None
        and gate["active_seconds"] >= cfg.GATE_LOCK_SECONDS
    )


@bp.get("/api/gate/status")
def gate_status():
    uid = _require_uid()
    cfg = _cfg()
    is_admin = _is_admin_uid(uid)
    gate = _repo().gate_get(uid)
    return jsonify({
        "activeSeconds": gate["active_seconds"],
        "thresholdSeconds": cfg.GATE_LOCK_SECONDS,
        "heartbeatSec": cfg.GATE_HEARTBEAT_SEC,
        "locked": _locked(cfg, gate, is_admin),
        "unlocked": gate["unlocked_at"] is not None,
        "isAdmin": is_admin,
    }), 200


@bp.post("/api/gate/heartbeat")
def gate_heartbeat():
    uid = _require_uid()
    cfg = _cfg()
    is_admin = _is_admin_uid(uid)
    body = parse_body(GateHeartbeatIn)
    secs = body.seconds if body.seconds is not None else cfg.GATE_HEARTBEAT_SEC
    secs = max(0, min(secs, 2 * cfg.GATE_HEARTBEAT_SEC))  # clamp resumed-tab jumps
    active = _repo().gate_add_seconds(uid, secs)
    gate = {"active_seconds": active, "unlocked_at": _repo().gate_get(uid)["unlocked_at"]}
    return jsonify({
        "activeSeconds": active,
        "locked": _locked(cfg, gate, is_admin),
        "unlocked": gate["unlocked_at"] is not None,
    }), 200


@bp.post("/api/gate/unlock")
def gate_unlock():
    uid = _require_uid()
    cfg = _cfg()
    body = parse_body(GateUnlockIn)
    stars = body.stars
    insight = body.insight.strip()
    if not (1 <= stars <= 5):
        raise ApiError("VALIDATION", "stars must be 1–5", 422)
    if len(insight) < MIN_INSIGHT:
        raise ApiError("VALIDATION", f"insight must be at least {MIN_INSIGHT} characters", 422)
    repo = _repo()
    already = repo.gate_get(uid)["unlocked_at"] is not None
    if already:
        return jsonify({"unlocked": True}), 200
    repo.feedback_add(uid, stars, insight)
    repo.gate_unlock(uid)
    u = repo.get_user_by_id(uid)
    admin_to = next(iter(cfg.ADMIN_EMAILS), None) or (cfg.SMTP_FROM or "")
    if admin_to:
        mailer.send_email(
            cfg, admin_to, "[ARUORA IELTS] New test feedback",
            f"User {getattr(u, 'email', uid)} rated {stars}/5.\n\nInsight:\n{insight}",
        )
    return jsonify({"unlocked": True}), 200


@bp.get("/api/admin/feedback")
def admin_feedback():
    _require_admin()
    return jsonify(_repo().feedback_list()), 200

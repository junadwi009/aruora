"""
Master-admin endpoints (Manage users) — WS03-07 hardened.

Admin is designated *server-side* via the ADMIN_EMAILS env var — never
self-service. A request is admin iff the signed-in account's email is in
ADMIN_EMAILS. There is no is_admin DB column, so admin can't be granted by a
DB write or an app bug — only by deployment config (a Secret / env var).

WS03-07 controls on top:
- append-only audit trail (admin_audit) for admin login, user deletion and
  admin-initiated password resets;
- password reauthentication (and TOTP when ADMIN_TOTP_SECRET is set) inside a
  short window before destructive actions (/api/admin/reauth);
- admin-initiated resets use the same single-use stateful token records as the
  self-service flow (never reusable, never logged);
- the same session + CSRF protections apply (enforced globally in app.session).

Residual risk for beta: the env allow-list remains until the normalized RBAC
model lands; the release gate must document it (16_RELEASE_GATES.md).
"""
from flask import Blueprint, current_app, jsonify, request

from app.errors import ApiError
from app.routes._deps import _cfg, _repo
from app.routes.account import _client_ip, throttle_or_429
from app.security import totp
from app.services import mailer
from app.session import current_uid, hash_ip, stamp_admin_reauth, reauth_age_seconds

bp = Blueprint("admin", __name__)


def _is_admin_email(email) -> bool:
    if not email:
        return False
    return email.strip().lower() in current_app.config["APP_CONFIG"].ADMIN_EMAILS


def _require_admin():
    """Return the signed-in admin UserProfile, or raise 401/403."""
    uid = current_uid()
    u = _repo().get_user_by_id(uid) if uid else None
    if u is None:
        raise ApiError("UNAUTHORIZED", "Not signed in", 401)
    if not _is_admin_email(u.email):
        raise ApiError("FORBIDDEN", "Admin access required", 403)
    return u


def _require_reauth(admin):
    """Destructive actions need a fresh password reauthentication (WS03-07)."""
    cfg = _cfg()
    age = reauth_age_seconds()
    if age is None or age > cfg.ADMIN_REAUTH_SECONDS:
        raise ApiError("REAUTH_REQUIRED", "Reauthentication required for this action", 403)
    if cfg.ADMIN_TOTP_SECRET:
        # The TOTP was already verified as part of /api/admin/reauth.
        pass


@bp.post("/api/admin/reauth")
def reauth():
    """Verify the admin's password (and TOTP when configured) and stamp the
    current session as freshly reauthenticated for ADMIN_REAUTH_SECONDS."""
    admin = _require_admin()
    cfg = _cfg()
    throttle_or_429("admin_reauth", admin.email, limit=5, window=300)
    b = request.get_json(force=True) or {}
    if not _repo().verify_password_for(admin.id, b.get("password") or ""):
        raise ApiError("UNAUTHORIZED", "Password incorrect", 401)
    if cfg.ADMIN_TOTP_SECRET and not totp.totp_verify(cfg.ADMIN_TOTP_SECRET, b.get("totp") or ""):
        raise ApiError("UNAUTHORIZED", "Valid admin TOTP code required", 401)
    stamp_admin_reauth()
    return jsonify({"ok": True, "reauthSeconds": cfg.ADMIN_REAUTH_SECONDS}), 200


@bp.get("/api/admin/users")
def list_users():
    _require_admin()
    return jsonify(_repo().list_accounts()), 200


@bp.get("/api/admin/stats")
def stats():
    _require_admin()
    return jsonify(_repo().admin_stats()), 200


@bp.get("/api/admin/audit")
def audit():
    _require_admin()
    return jsonify(_repo().list_audit()), 200


@bp.delete("/api/admin/users/<int:user_id>")
def delete_user(user_id):
    admin = _require_admin()
    if user_id == admin.id:
        raise ApiError("VALIDATION", "Use Settings → Data to delete your own account", 400)
    _require_reauth(admin)
    if not _repo().delete_account(user_id):
        raise ApiError("NOT_FOUND", "User not found", 404)
    _repo().add_audit("delete_user", actor_user_id=admin.id, actor_email=admin.email,
                      target_user_id=user_id, ip_hash=hash_ip(_client_ip()))
    return jsonify({"ok": True}), 200


@bp.post("/api/admin/users/<int:user_id>/reset-password")
def reset_user_password(user_id):
    admin = _require_admin()
    _require_reauth(admin)
    u = _repo().get_user_by_id(user_id)
    if u is None or not u.email:
        raise ApiError("NOT_FOUND", "User (with an email) not found", 404)
    cfg = _cfg()
    # Single-use stateful token (same records as self-service reset).
    token = _repo().create_one_time_token(
        "reset", u.id, ttl_min=60,
        ip_hash=hash_ip(_client_ip()), ua=request.headers.get("User-Agent") or "",
    )
    link = f"{cfg.APP_BASE_URL}/?reset_token={token}"
    delivered = mailer.send_email(
        cfg, u.email, "Reset your password",
        "An administrator initiated a password reset for your account. "
        f"Open this link within 1 hour:\n\n{link}\n\n"
        "If you didn't expect this, contact support.",
    )
    _repo().add_audit("reset_user_password", actor_user_id=admin.id,
                      actor_email=admin.email, target_user_id=user_id,
                      detail={"delivered": bool(delivered)},
                      ip_hash=hash_ip(_client_ip()))
    # Revoke the target's sessions: a reset is also an account-takeover response.
    current_app.config["SESSIONS"].revoke_all_for_user(u.id)
    return jsonify({"ok": True, "delivered": bool(delivered)}), 200


# ── WS07-08: AI provider budget + emergency kill-switch ──────────────────────

@bp.get("/api/admin/ai-budget")
def ai_budget_status():
    _require_admin()
    from app.costguard import ai_halt_reason, AI_HALTED_FLAG
    from datetime import datetime, timedelta, timezone

    cfg = _cfg()
    repo = _repo()
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return jsonify({
        "halted": ai_halt_reason(cfg, repo) is not None,
        "reason": ai_halt_reason(cfg, repo),
        "killSwitchEnv": bool(cfg.AI_BUDGET_KILL),
        "adminHalt": (repo.flag_get(AI_HALTED_FLAG) or "") != "",
        "dailyBudgetMicros": cfg.AI_DAILY_BUDGET_MICROS,
        "spentTodayMicros": repo.ledger_sum_cost(start, now + timedelta(seconds=1)),
    }), 200


@bp.post("/api/admin/ai-budget")
def ai_budget_set():
    """Set/clear the admin AI halt flag. The env kill-switch (AI_BUDGET_KILL)
    cannot be cleared from here — deployment config only (fail closed)."""
    admin = _require_admin()
    from app.costguard import AI_HALTED_FLAG

    b = request.get_json(force=True) or {}
    halt = bool(b.get("halt"))
    repo = _repo()
    repo.flag_set(AI_HALTED_FLAG, "1" if halt else "")
    _repo().add_audit("ai_budget_halt" if halt else "ai_budget_resume",
                      actor_user_id=admin.id, actor_email=admin.email,
                      ip_hash=hash_ip(_client_ip()))
    return jsonify({"ok": True, "halt": halt}), 200

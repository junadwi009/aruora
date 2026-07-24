"""
Master-admin endpoints (Manage users).

Admin is designated *server-side* via the ADMIN_EMAILS env var — never
self-service. A request is admin iff the signed-in account's email is in
ADMIN_EMAILS. There is no is_admin DB column, so admin can't be granted by a
DB write or an app bug — only by deployment config (a Secret / env var).

Privacy: admin manages the *account list* (who exists, usage counts) and can
remove or password-reset a user. It does NOT expose other users' essays or
answers, but it DOES surface submitted test-phase feedback (star rating +
insight text) for review via /api/admin/feedback.
"""
from flask import Blueprint, current_app, jsonify
from itsdangerous import URLSafeTimedSerializer

from app.errors import ApiError
from app.routes._deps import _cfg, _repo
from app.services import mailer
from app.session import current_uid

bp = Blueprint("admin", __name__)

# Must match account.py so the emailed link is consumable by /api/account/reset.
_RESET_SALT = "ielts-password-reset"


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


@bp.get("/api/admin/users")
def list_users():
    _require_admin()
    return jsonify(_repo().list_accounts()), 200


@bp.get("/api/admin/stats")
def stats():
    _require_admin()
    return jsonify(_repo().admin_stats()), 200


@bp.delete("/api/admin/users/<int:user_id>")
def delete_user(user_id):
    admin = _require_admin()
    if user_id == admin.id:
        raise ApiError("VALIDATION", "Use Settings → Data to delete your own account", 400)
    if not _repo().delete_account(user_id):
        raise ApiError("NOT_FOUND", "User not found", 404)
    return jsonify({"ok": True}), 200


@bp.post("/api/admin/users/<int:user_id>/reset-password")
def reset_user_password(user_id):
    _require_admin()
    u = _repo().get_user_by_id(user_id)
    if u is None or not u.email:
        raise ApiError("NOT_FOUND", "User (with an email) not found", 404)
    cfg = _cfg()
    token = URLSafeTimedSerializer(cfg.SESSION_SECRET, salt=_RESET_SALT).dumps(u.id)
    link = f"{cfg.APP_BASE_URL}/?reset_token={token}"
    mailer.send_email(
        cfg, u.email, "Reset your IELTS Coach password",
        "An administrator initiated a password reset for your account. "
        f"Open this link within 1 hour:\n\n{link}\n\n"
        "If you didn't expect this, you can ignore this email.",
    )
    return jsonify({"ok": True}), 200

"""
Phase 3a — account identity + auth.

- POST /api/account/register {email,password} → create/attach + log in
- POST /api/account/login {email,password}    → log in
- POST /api/account/logout
- GET  /api/account/me                          → current profile or 401
"""
import re

from flask import Blueprint, current_app, jsonify, request
from itsdangerous import BadData, URLSafeTimedSerializer

from app.errors import ApiError
from app.routes._deps import _repo, _cfg
from app.services import mailer
from app.session import login_session, current_uid, clear_session

bp = Blueprint("account", __name__)

_RESET_SALT = "ielts-password-reset"
_RESET_MAX_AGE = 3600  # 1 hour


def _reset_serializer():
    return URLSafeTimedSerializer(current_app.config["APP_CONFIG"].SESSION_SECRET, salt=_RESET_SALT)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_admin(email) -> bool:
    if not email:
        return False
    return email.strip().lower() in current_app.config["APP_CONFIG"].ADMIN_EMAILS


def _public(u) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name,
            "goal": u.goal, "targetBand": u.target_band,
            "skillTargets": u.skill_targets or {},
            "country": u.country, "examDate": u.exam_date, "bio": u.bio,
            "avatar": u.avatar, "reminderTime": u.reminder_time,
            "reminderTz": u.reminder_tz,
            "isAdmin": _is_admin(u.email)}


@bp.post("/api/account/register")
def register():
    b = request.get_json(force=True) or {}
    email = (b.get("email") or "").strip().lower()
    password = b.get("password") or ""
    if not _EMAIL_RE.match(email):
        raise ApiError("VALIDATION", "A valid email is required", 422)
    if len(password) < 6:
        raise ApiError("VALIDATION", "Password must be at least 6 characters", 422)

    repo = _repo()
    if repo.get_account_by_email(email) is not None:
        raise ApiError("VALIDATION", "That email is already registered", 422)

    # Attach to the current anonymous session profile if it has no email yet.
    uid = current_uid()
    existing = repo.get_user_by_id(uid) if uid else None
    if existing is not None and not existing.email:
        u = repo.attach_credentials(existing.id, email, password)
    else:
        u = repo.create_account(email, password)
    login_session(u.id)
    return jsonify(_public(u)), 200


@bp.post("/api/account/login")
def login():
    b = request.get_json(force=True) or {}
    email = (b.get("email") or "").strip().lower()
    u = _repo().verify_login(email, b.get("password") or "")
    if u is None:
        raise ApiError("UNAUTHORIZED", "Incorrect email or password", 401)
    login_session(u.id, remember=bool(b.get("remember")))
    return jsonify(_public(u)), 200


@bp.post("/api/account/logout")
def logout():
    clear_session()
    return jsonify({"ok": True}), 200


def verify_google_id_token(token: str, client_id: str):
    """Verify a Google ID token against client_id; return its claims, or None.

    Isolated as a module function so tests can monkeypatch it. google-auth is
    imported lazily so importing this module needs no Google dependency.
    """
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        return id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
    except Exception:
        return None


@bp.post("/api/account/google")
def google_login():
    """Sign in with Google: verify the ID token, then find/create by google_sub."""
    cfg = _cfg()
    if not cfg.GOOGLE_CLIENT_ID:
        raise ApiError("NOT_CONFIGURED", "Google sign-in is not configured", 501)
    token = (request.get_json(force=True) or {}).get("credential") or ""
    claims = verify_google_id_token(token, cfg.GOOGLE_CLIENT_ID)
    if not claims or not claims.get("sub"):
        raise ApiError("UNAUTHORIZED", "Invalid Google token", 401)
    u = _repo().upsert_google_user(
        claims["sub"], (claims.get("email") or "").strip().lower(), claims.get("name") or "",
    )
    login_session(u.id)
    return jsonify(_public(u)), 200


@bp.post("/api/account/forgot")
def forgot():
    """Email a reset link if the account exists. Always 200 (no enumeration)."""
    email = ((request.get_json(force=True) or {}).get("email") or "").strip().lower()
    u = _repo().get_account_by_email(email) if email else None
    if u is not None:
        token = _reset_serializer().dumps(u.id)
        cfg = _cfg()
        link = f"{cfg.APP_BASE_URL}/?reset_token={token}"
        mailer.send_email(
            cfg, email, "Reset your IELTS Coach password",
            f"Someone asked to reset your password. Open this link within 1 hour:\n\n{link}\n\n"
            "If this wasn't you, you can ignore this email.",
        )
    return jsonify({"ok": True}), 200


@bp.post("/api/account/reset")
def reset():
    b = request.get_json(force=True) or {}
    new = b.get("newPassword") or ""
    if len(new) < 6:
        raise ApiError("VALIDATION", "New password must be at least 6 characters", 422)
    try:
        uid = _reset_serializer().loads(b.get("token", ""), max_age=_RESET_MAX_AGE)
    except BadData:
        raise ApiError("VALIDATION", "This reset link is invalid or has expired", 400)
    if _repo().get_user_by_id(uid) is None:
        raise ApiError("VALIDATION", "This reset link is invalid or has expired", 400)
    _repo().set_password(uid, new)
    return jsonify({"ok": True}), 200


@bp.get("/api/account/me")
def me():
    uid = current_uid()
    u = _repo().get_user_by_id(uid) if uid else None
    if u is None:
        raise ApiError("UNAUTHORIZED", "Not signed in", 401)
    return jsonify(_public(u)), 200


def _uid_or_401() -> int:
    uid = current_uid()
    if uid is None:
        raise ApiError("UNAUTHORIZED", "Not signed in", 401)
    return uid


@bp.patch("/api/account/profile")
def update_profile():
    b = request.get_json(force=True) or {}
    _repo().update_profile(_uid_or_401(), b)
    return jsonify(_public(_repo().get_user_by_id(current_uid()))), 200


_MAX_AVATAR = 3_000_000  # ~2 MB image as a base64 data URL


@bp.post("/api/account/avatar")
def set_avatar():
    b = request.get_json(force=True) or {}
    data_url = b.get("dataUrl", "")
    if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        raise ApiError("VALIDATION", "Avatar must be an image data URL", 422)
    if len(data_url) > _MAX_AVATAR:
        raise ApiError("VALIDATION", "Image is too large (max ~2 MB)", 422)
    _repo().set_avatar(_uid_or_401(), data_url)
    return jsonify({"ok": True}), 200


@bp.get("/api/account/export")
def export_data():
    return jsonify(_repo().export_data(_uid_or_401())), 200


@bp.delete("/api/account")
def delete_account():
    _repo().delete_account(_uid_or_401())
    clear_session()
    return jsonify({"ok": True}), 200


@bp.post("/api/account/password")
def change_password():
    b = request.get_json(force=True) or {}
    new = b.get("newPassword") or ""
    if len(new) < 6:
        raise ApiError("VALIDATION", "New password must be at least 6 characters", 422)
    if not _repo().change_password(_uid_or_401(), b.get("currentPassword") or "", new):
        raise ApiError("UNAUTHORIZED", "Current password is incorrect", 401)
    return jsonify({"ok": True}), 200

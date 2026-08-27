"""
WS03 — account identity + auth.

- POST /api/account/register {email,password} → create + email verification + log in
- POST /api/account/login {email,password}    → log in (rotates session id)
- POST /api/account/logout                    → revokes the server-side session
- POST /api/account/verify {token}            → single-use email ownership proof
- POST /api/account/verify/resend             → rate-limited resend
- POST /api/account/forgot / reset            → stateful single-use reset tokens
- GET  /api/account/me                        → current profile or 401
- GET/DELETE /api/account/sessions            → session-management UX (WS03-09)

Session identifiers are opaque server-side records (app.session). Password
policy and hashing live in app.security.passwords (WS03-04). Every auth flow
is throttled against a shared store (WS03-08) and never becomes an
enumeration oracle.
"""
import re

from flask import Blueprint, current_app, jsonify, request

from app.errors import ApiError
from app.routes._deps import _repo, _cfg
from app.security import passwords
from app.security.passwords import validate_new_password
from app.services import mailer
from app.session import (
    login_session, current_uid, clear_session, hash_ip,
)

bp = Blueprint("account", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── WS03-08: shared-store abuse throttles ────────────────────────────────────

def _client_ip() -> str:
    return request.headers.get("X-Real-IP") or request.remote_addr or "unknown"


def throttle_or_429(kind: str, acct: str | None, *, limit: int, window: int) -> None:
    """Count an attempt per client and per account; 429 when over `limit`
    within `window` seconds. Counters live in the shared KV store so all API
    processes enforce the same budget."""
    kv = current_app.config["KV"]
    keys = [f"att:{kind}:ip:{hash_ip(_client_ip())}"]
    if acct:
        keys.append(f"att:{kind}:acct:{acct}")
    for k in keys:
        if kv.incr(k, window) > limit:
            raise ApiError(
                "RATE_LIMITED",
                "Too many attempts — please wait and try again",
                429, details={"retryAfter": max(1, int(kv.ttl(k)))},
            )


def _backoff_active(kind: str, acct: str) -> int:
    """Seconds remaining in a progressive backoff window, 0 when clear."""
    kv = current_app.config["KV"]
    ttl = kv.ttl(f"bo:{kind}:acct:{acct}")
    return max(0, int(ttl))


def _register_failure(kind: str, acct: str, *, base: int = 15, cap: int = 900) -> None:
    """Progressive delay after repeated failures. Deliberately NOT a permanent
    lockout: the block decays and later failures only extend the wait up to
    `cap`, so an attacker cannot permanently lock a victim out."""
    kv = current_app.config["KV"]
    fails = kv.incr(f"fail:{kind}:acct:{acct}", 900)
    if fails >= 5:
        delay = min(base * (2 ** (fails - 5)), cap)
        kv.set(f"bo:{kind}:acct:{acct}", "1", delay)


def _require_password(pw: str, email: str = "") -> str:
    problems = validate_new_password(pw or "", min_chars=_cfg().MIN_PASSWORD_CHARS,
                                     context=email)
    if problems:
        raise ApiError("VALIDATION", "; ".join(problems), 422)
    return pw


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
            # Whether a local password is set — lets Google-only users add one.
            "hasPassword": bool(u.password_hash),
            # WS03-05: email ownership state for UI nudges.
            "emailVerified": bool(getattr(u, "email_verified", False)),
            "isAdmin": _is_admin(u.email)}


def _send_verify_email(u) -> None:
    """Email a single-use verification link. Delivery metadata is logged by the
    mailer; the token/URL is never logged anywhere."""
    cfg = _cfg()
    repo = _repo()
    token = repo.create_one_time_token(
        "verify", u.id, ttl_min=cfg.VERIFY_TOKEN_MIN,
        ip_hash=hash_ip(_client_ip()), ua=request.headers.get("User-Agent") or "",
    )
    link = f"{cfg.APP_BASE_URL}/?verify_token={token}"
    mailer.send_email(
        cfg, u.email, "Verify your email",
        "Welcome! Confirm this email address to unlock everything:\n\n"
        f"{link}\n\nThe link expires in {cfg.VERIFY_TOKEN_MIN // 60} hours.",
    )


@bp.post("/api/account/register")
def register():
    b = request.get_json(force=True) or {}
    email = (b.get("email") or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise ApiError("VALIDATION", "A valid email is required", 422)
    _require_password(b.get("password") or "", email)

    repo = _repo()
    if repo.get_account_by_email(email) is not None:
        raise ApiError("VALIDATION", "That email is already registered", 422)

    # Attach to the current anonymous session profile if it has no email yet.
    uid = current_uid()
    existing = repo.get_user_by_id(uid) if uid else None
    if existing is not None and not existing.email:
        u = repo.attach_credentials(existing.id, email, b.get("password"))
    else:
        u = repo.create_account(email, b.get("password"))
    # WS03-05: prove email ownership before expensive features unlock.
    try:
        _send_verify_email(u)
    except Exception:  # noqa: BLE001 — verification email must not block signup
        current_app.logger.warning("verify email dispatch failed outcome=error")
    login_session(u.id)

    # WS21 — signup_completed is server-authoritative (only emitted on a real
    # account creation/attachment). Acquisition dims validated server-side.
    from app.routes._analytics import capture_acquisition, emit
    capture_acquisition(u.id)
    emit("signup_completed", user_id=u.id)
    return jsonify(_public(u)), 200


@bp.post("/api/account/login")
def login():
    b = request.get_json(force=True) or {}
    email = (b.get("email") or "").strip().lower()
    cfg = _cfg()
    repo = _repo()
    if email:
        wait = _backoff_active("login", email)
        if wait:
            raise ApiError("UNAUTHORIZED", "Too many failed attempts — try again shortly",
                           429, details={"retryAfter": wait})
    throttle_or_429("login", email or None, limit=10, window=60)
    u = repo.verify_login(email, b.get("password") or "")
    if u is None:
        if email:
            _register_failure("login", email)
        raise ApiError("UNAUTHORIZED", "Incorrect email or password", 401)
    # WS03-07: optional mandatory MFA for admin accounts.
    if _is_admin(u.email) and cfg.ADMIN_TOTP_SECRET:
        from app.security import totp

        if not totp.totp_verify(cfg.ADMIN_TOTP_SECRET, (b.get("totp") or "")):
            raise ApiError("UNAUTHORIZED", "Valid admin TOTP code required", 401)
    # WS03-04: transparent rehash — legacy hashes migrate on successful login.
    if u.password_hash and passwords.needs_rehash(u.password_hash):
        repo.set_password(u.id, b.get("password") or "")
    if _is_admin(u.email):
        repo.add_audit("admin.login", actor_user_id=u.id, actor_email=u.email,
                       ip_hash=hash_ip(_client_ip()))
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
    """Sign in with Google: verify the ID token (issuer/audience/signature/
    expiry all checked by verify_google_id_token), then find/create by sub."""
    cfg = _cfg()
    if not cfg.GOOGLE_CLIENT_ID:
        raise ApiError("NOT_CONFIGURED", "Google sign-in is not configured", 501)
    throttle_or_429("google", None, limit=20, window=300)
    token = (request.get_json(force=True) or {}).get("credential") or ""
    claims = verify_google_id_token(token, cfg.GOOGLE_CLIENT_ID)
    if not claims or not claims.get("sub"):
        raise ApiError("UNAUTHORIZED", "Invalid Google token", 401)
    # Only trust the email if Google says it's verified — otherwise an attacker
    # could set an unverified address and get linked to that account. Sign-in by
    # google_sub still works; the email is simply not adopted.
    verified = bool(claims.get("email_verified"))
    email = (claims.get("email") or "").strip().lower() if verified else ""
    u, is_new = _repo().upsert_google_user(claims["sub"], email,
                                           claims.get("name") or "",
                                           email_verified=verified)
    if _is_admin(u.email) and cfg.ADMIN_TOTP_SECRET:
        from app.security import totp

        if not totp.totp_verify(cfg.ADMIN_TOTP_SECRET, ((request.get_json(force=True) or {}).get("totp") or "")):
            raise ApiError("UNAUTHORIZED", "Valid admin TOTP code required", 401)
    if _is_admin(u.email):
        _repo().add_audit("admin.login", actor_user_id=u.id, actor_email=u.email,
                          ip_hash=hash_ip(_client_ip()), detail={"via": "google"})
    login_session(u.id)
    # WS21: Google sign-in that created a new account counts as signup.
    if is_new:
        from app.routes._analytics import emit
        emit("signup_completed", user_id=u.id)
    # isNew tells the client to route a first-time Google user into the placement
    # flow; returning users go straight to the dashboard.
    return jsonify({**_public(u), "isNew": is_new}), 200


@bp.post("/api/account/forgot")
def forgot():
    """Email a single-use reset link if the account exists. Always 200 (no
    enumeration); throttled per account (mail-bombing) and per client."""
    email = ((request.get_json(force=True) or {}).get("email") or "").strip().lower()
    throttle_or_429("forgot_ip", None, limit=10, window=3600)
    u = _repo().get_account_by_email(email) if email else None
    if u is not None:
        throttle_or_429("forgot_acct", email, limit=3, window=3600)
        cfg = _cfg()
        token = _repo().create_one_time_token(
            "reset", u.id, ttl_min=60,
            ip_hash=hash_ip(_client_ip()), ua=request.headers.get("User-Agent") or "",
        )
        link = f"{cfg.APP_BASE_URL}/?reset_token={token}"
        mailer.send_email(
            cfg, email, "Reset your password",
            "Someone asked to reset your password. Open this link within 1 hour:\n\n"
            f"{link}\n\nIf this wasn't you, you can ignore this email.",
        )
    return jsonify({"ok": True}), 200


@bp.post("/api/account/reset")
def reset():
    """Consume a one-time token, set the new password, revoke every active
    session and any outstanding tokens. Failures are generic (no oracle)."""
    b = request.get_json(force=True) or {}
    throttle_or_429("reset", None, limit=10, window=3600)
    _require_password(b.get("newPassword") or "")
    repo = _repo()
    uid = repo.consume_one_time_token("reset", b.get("token") or "")
    if uid is None:
        raise ApiError("VALIDATION", "This reset link is invalid or has expired", 400)
    repo.set_password(uid, b.get("newPassword"))
    repo.invalidate_one_time_tokens(uid, ("reset", "verify"))
    current_app.config["SESSIONS"].revoke_all_for_user(uid)
    return jsonify({"ok": True}), 200


@bp.post("/api/account/verify")
def verify_email():
    """Consume a single-use email-verification token (WS03-05)."""
    b = request.get_json(force=True) or {}
    throttle_or_429("verify", None, limit=20, window=3600)
    uid = _repo().consume_one_time_token("verify", b.get("token") or "")
    if uid is None:
        raise ApiError("VALIDATION", "This verification link is invalid or has expired", 400)
    _repo().set_email_verified(uid, True)
    return jsonify({"ok": True}), 200


@bp.post("/api/account/verify/resend")
def resend_verification():
    """Resend the verification email (authenticated, rate-limited, generic)."""
    uid = _uid_or_401()
    u = _repo().get_user_by_id(uid)
    if u is None or not u.email or u.email_verified:
        return jsonify({"ok": True}), 200  # generic — no state oracle
    throttle_or_429("verify_resend", u.email, limit=3, window=3600)
    _send_verify_email(u)
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
    # Reject SVG: it can embed <script>/onload and would execute if the data URL
    # is ever rendered outside an <img> (e.g. as a background or opened directly).
    if data_url[:20].lower().startswith("data:image/svg"):
        raise ApiError("VALIDATION", "SVG avatars are not allowed", 422)
    if len(data_url) > _MAX_AVATAR:
        raise ApiError("VALIDATION", "Image is too large (max ~2 MB)", 422)
    _repo().set_avatar(_uid_or_401(), data_url)
    return jsonify({"ok": True}), 200


@bp.get("/api/account/export")
def export_data():
    uid = _uid_or_401()
    # WS10-05: durable audit of data-subject export requests.
    try:
        _repo().add_audit("user.export", actor_user_id=uid,
                          target_user_id=uid, ip_hash=hash_ip(_client_ip()))
    except Exception:
        pass
    return jsonify(_repo().export_data(uid)), 200


@bp.delete("/api/account")
def delete_account():
    uid = _uid_or_401()
    # WS10-05: durable audit of data-subject deletion (actor id denormalised
    # into the audit row; the FK is SET NULL on purge by design).
    try:
        u = _repo().get_user_by_id(uid)
        _repo().add_audit("user.delete", actor_user_id=uid,
                          actor_email=(u.email if u else "") or "",
                          target_user_id=uid, ip_hash=hash_ip(_client_ip()))
    except Exception:
        pass
    _repo().delete_account(uid)  # cascades auth_session + tokens by schema
    clear_session()
    return jsonify({"ok": True}), 200


@bp.post("/api/account/password")
def change_password():
    b = request.get_json(force=True) or {}
    new = b.get("newPassword") or ""
    uid = _uid_or_401()
    repo = _repo()
    # Google-only accounts have no local password yet: let the signed-in user set
    # one without proving a current password (there is none to prove).
    if not repo.has_password(uid):
        _require_password(new)
        repo.set_password(uid, new)
    else:
        _require_password(new)
        if not repo.change_password(uid, b.get("currentPassword") or "", new):
            raise ApiError("UNAUTHORIZED", "Current password is incorrect", 401)
    # WS03-01: password change revokes every OTHER session (this one survives).
    from app.session import current_session

    row = current_session()
    current_app.config["SESSIONS"].revoke_all_for_user(
        uid, except_hash=row.id if row is not None else None)
    repo.invalidate_one_time_tokens(uid, ("reset",))
    return jsonify({"ok": True}), 200


# ── WS03-09: session-management UX ───────────────────────────────────────────

@bp.get("/api/account/sessions")
def list_sessions():
    uid = _uid_or_401()
    store = current_app.config["SESSIONS"]
    from app.session import current_session

    row = current_session()
    out = []
    for s in store.list_for_user(uid):
        out.append({
            "current": bool(row is not None and s.id == row.id),
            "device": s.device or "",
            "remember": bool(s.remember),
            "createdAt": s.created_at.isoformat() if s.created_at else None,
            "lastSeenAt": s.last_seen_at.isoformat() if s.last_seen_at else None,
        })
    return jsonify(out), 200


@bp.delete("/api/account/sessions/others")
def revoke_other_sessions():
    uid = _uid_or_401()
    from app.session import current_session

    row = current_session()
    n = current_app.config["SESSIONS"].revoke_all_for_user(
        uid, except_hash=row.id if row is not None else None)
    return jsonify({"revoked": n}), 200


@bp.delete("/api/account/sessions")
def revoke_all_sessions():
    """Log out every device, including this one."""
    uid = _uid_or_401()
    n = current_app.config["SESSIONS"].revoke_all_for_user(uid)
    clear_session()
    return jsonify({"revoked": n}), 200

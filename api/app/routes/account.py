"""
Phase 3a — account identity + auth.

- POST /api/account/register {email,password} → create/attach + log in
- POST /api/account/login {email,password}    → log in
- POST /api/account/logout
- GET  /api/account/me                          → current profile or 401
"""
import re

from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _repo
from app.session import login_session, current_uid, clear_session

bp = Blueprint("account", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _public(u) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name,
            "goal": u.goal, "targetBand": u.target_band}


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
    login_session(u.id)
    return jsonify(_public(u)), 200


@bp.post("/api/account/logout")
def logout():
    clear_session()
    return jsonify({"ok": True}), 200


@bp.get("/api/account/me")
def me():
    uid = current_uid()
    u = _repo().get_user_by_id(uid) if uid else None
    if u is None:
        raise ApiError("UNAUTHORIZED", "Not signed in", 401)
    return jsonify(_public(u)), 200

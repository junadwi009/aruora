"""
Phase 2e-1 — optional passcode gate.

When APP_PASSCODE is empty the app is open (offline-dev default). When set, all
/api/* routes except health + these auth endpoints require a session established
via POST /api/auth/login.
"""
from flask import Blueprint, current_app, jsonify, request, session

from app.errors import ApiError

bp = Blueprint("auth", __name__)


def _passcode() -> str:
    return current_app.config["APP_CONFIG"].APP_PASSCODE or ""


@bp.get("/api/auth/status")
def auth_status():
    required = bool(_passcode())
    return jsonify({
        "authRequired": required,
        "authenticated": (not required) or bool(session.get("auth")),
    }), 200


@bp.post("/api/auth/login")
def auth_login():
    code = _passcode()
    if not code:
        return jsonify({"ok": True}), 200  # auth disabled
    given = (request.get_json(force=True) or {}).get("passcode", "")
    if given != code:
        raise ApiError("UNAUTHORIZED", "Incorrect passcode", 401)
    session["auth"] = True
    return jsonify({"ok": True}), 200


@bp.post("/api/auth/logout")
def auth_logout():
    session.clear()
    return jsonify({"ok": True}), 200

"""
Phase 2e-1 — optional passcode gate (WS03: now backed by the server-side
session store, so grants are revocable and expire server-side).

When APP_PASSCODE is empty the app is open (offline-dev default). When set, all
/api/* routes except health + these auth endpoints require a session granted
via POST /api/auth/login.
"""
import hmac

from flask import Blueprint, current_app, jsonify

from app.errors import ApiError
from app.schemas import PasscodeLoginIn
from app.session import clear_session, gate_authenticated, current_uid, grant_gate
from app.validation import parse_body

bp = Blueprint("auth", __name__)


def _passcode() -> str:
    return current_app.config["APP_CONFIG"].APP_PASSCODE or ""


@bp.get("/api/auth/status")
def auth_status():
    required = bool(_passcode())
    return jsonify({
        "authRequired": required,
        "authenticated": (not required) or gate_authenticated() or current_uid() is not None,
    }), 200


@bp.post("/api/auth/login")
def auth_login():
    code = _passcode()
    if not code:
        return jsonify({"ok": True}), 200  # auth disabled
    # WS03-08: shared-store throttle on passcode guesses per client.
    from app.routes.account import throttle_or_429

    throttle_or_429("authlogin", None, limit=20, window=300)
    given = parse_body(PasscodeLoginIn).passcode
    if not hmac.compare_digest(str(given), str(code)):  # constant-time
        raise ApiError("UNAUTHORIZED", "Incorrect passcode", 401)
    grant_gate()
    return jsonify({"ok": True}), 200


@bp.post("/api/auth/logout")
def auth_logout():
    clear_session()
    return jsonify({"ok": True}), 200

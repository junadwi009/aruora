"""
Dependency helpers for route modules.

Each helper reads from Flask's current_app.config, which is populated
by create_app() either with real instances (production path) or with
test-injected mocks (TESTING path).
"""
from flask import current_app

from app.errors import ApiError
from app.session import current_uid


def _repo():
    return current_app.config["REPO"]


def _gateway():
    return current_app.config["GATEWAY"]


def _cfg():
    return current_app.config["APP_CONFIG"]


def _uid():
    """Current session user id, or None (anonymous / not signed in)."""
    return current_uid()


def _require_uid() -> int:
    """Current session user id, or 401 — for routes that own/write user data."""
    uid = current_uid()
    if uid is None:
        raise ApiError("UNAUTHORIZED", "Sign in to continue", 401)
    return uid

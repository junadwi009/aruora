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


def _jobs():
    """WS07 JobService (None on the bare health-test path)."""
    return current_app.config.get("JOBS")


def _concurrency():
    """WS07 per-user heavy-op concurrency guard (None on the bare path)."""
    return current_app.config.get("CONCURRENCY")


def _lang() -> str:
    """UI language for this request, from the X-Lang header. 'id' or 'en'.

    Used to localize learner-facing LLM prose (feedback, lessons, pronunciation
    tips). Practice content the learner is tested on stays English regardless.
    """
    from flask import request
    return "id" if (request.headers.get("X-Lang") or "").strip().lower() == "id" else "en"


def _uid():
    """Current session user id, or None (anonymous / not signed in)."""
    return current_uid()


def _require_uid() -> int:
    """Current session user id, or 401 — for routes that own/write user data."""
    uid = current_uid()
    if uid is None:
        raise ApiError("UNAUTHORIZED", "Sign in to continue", 401)
    return uid

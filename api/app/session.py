"""
Session helpers for Phase 3a auth. `_now` is a module-level indirection so tests
can fast-forward the clock to exercise the idle timeout.
"""
from datetime import datetime, timezone

from flask import session


def _now() -> datetime:
    return datetime.now(timezone.utc)


def login_session(uid: int, remember: bool = False) -> None:
    session["uid"] = uid
    session["last_seen"] = _now().isoformat()
    session["remember"] = bool(remember)
    # A remembered session is permanent, so its cookie survives a browser restart
    # (bounded by app.permanent_session_lifetime); otherwise it's a session cookie.
    session.permanent = bool(remember)


def current_uid():
    return session.get("uid")


def touch() -> None:
    session["last_seen"] = _now().isoformat()


def clear_session() -> None:
    session.clear()

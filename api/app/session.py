"""WS03-01/02/03 — server-side sessions, rotation, and CSRF.

The browser stores only an opaque random token in an HttpOnly cookie
(``ar_sid``). All state lives server-side (``auth_session`` table — a shared
store across every worker; revocation is instant and central):

  - login / register / Google / reset rotate the identifier (old id dies);
  - logout invalidates the server row;
  - password change/reset and "log out all devices" revoke by user;
  - idle and absolute expiry are enforced server-side;
  - each session carries a CSRF token (double submit: HttpOnly session cookie
    plus a JS-readable ``ar_csrf`` cookie that unsafe requests must echo in the
    ``X-CSRF-Token`` header), and cross-site Origin/Referer are rejected.

Stored state is minimal: user id, csrf token, small flags (passcode gate,
admin reauth stamp), remember flag, device metadata. No password hashes, no
learner content. ``_now`` is a module-level indirection so tests can
fast-forward the clock to exercise idle/absolute expiry.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from flask import g, request
from werkzeug.test import Client as _WerkzeugClient

COOKIE_NAME = "ar_sid"
CSRF_COOKIE = "ar_csrf"
CSRF_HEADER = "X-CSRF-Token"
_UNSAFE = ("POST", "PUT", "PATCH", "DELETE")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def hash_ip(ip: str | None) -> str:
    """Privacy-safe network reference for audit metadata (never a raw IP)."""
    return _hash_token(ip or "unknown")[:32]


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; always compare in UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class SessionStore:
    """CRUD for server-side session rows (shares the repository's engine)."""

    def __init__(self, session_factory) -> None:
        self._sf = session_factory

    def _model(self):
        from .data.models import AuthSession

        return AuthSession

    def create(self, *, user_id: int | None, csrf_token: str, remember: bool,
               device: str, ip_hash: str, flags: dict, idle_min: float,
               absolute_min: float) -> tuple[str, object]:
        """Create a session; returns (raw_token, detached row)."""
        raw = secrets.token_urlsafe(32)
        model = self._model()
        now = _now()
        with self._sf() as s:
            row = model(
                id=_hash_token(raw), user_id=user_id, csrf_token=csrf_token,
                flags=dict(flags or {}), remember=bool(remember),
                device=(device or "")[:200], ip_hash=ip_hash or "",
                created_at=now, last_seen_at=now,
                absolute_expires_at=now + timedelta(minutes=absolute_min),
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            s.expunge(row)
        return raw, row

    def get(self, raw_token: str):
        """Return (row, status) with status in ok/expired/unknown. Expired rows
        are revoked on sight (fail closed)."""
        if not raw_token:
            return None, "unknown"
        model = self._model()
        now = _now()
        with self._sf() as s:
            row = s.get(model, _hash_token(raw_token))
            if row is None:
                return None, "unknown"
            if row.revoked_at is not None:
                s.expunge(row)
                return row, "expired"
            if row.absolute_expires_at is not None and _aware(row.absolute_expires_at) <= now:
                row.revoked_at = now
                s.commit()
                s.expunge(row)
                return row, "expired"
            s.expunge(row)
            return row, "ok"

    def touch(self, token_hash: str) -> None:
        with self._sf() as s:
            row = s.get(self._model(), token_hash)
            if row is not None and row.revoked_at is None:
                row.last_seen_at = _now()
                s.commit()

    def revoke(self, raw_token: str) -> None:
        if not raw_token:
            return
        with self._sf() as s:
            row = s.get(self._model(), _hash_token(raw_token))
            if row is not None and row.revoked_at is None:
                row.revoked_at = _now()
                s.commit()

    def revoke_all_for_user(self, user_id: int, except_hash: str | None = None) -> int:
        now = _now()
        with self._sf() as s:
            model = self._model()
            q = s.query(model).filter(
                model.user_id == user_id, model.revoked_at.is_(None)
            )
            if except_hash:
                q = q.filter(model.id != except_hash)
            n = q.update({model.revoked_at: now}, synchronize_session=False)
            s.commit()
            return n

    def set_flags(self, token_hash: str, flags: dict) -> None:
        with self._sf() as s:
            row = s.get(self._model(), token_hash)
            if row is not None and row.revoked_at is None:
                row.flags = dict(flags)
                s.commit()

    def list_for_user(self, user_id: int):
        """Active (non-revoked) sessions for the session-management UX."""
        from sqlalchemy import select

        model = self._model()
        now = _now()
        with self._sf() as s:
            rows = s.execute(
                select(model)
                .where(model.user_id == user_id, model.revoked_at.is_(None))
                .order_by(model.last_seen_at.desc())
            ).scalars().all()
            out = []
            for r in rows:
                if r.absolute_expires_at is not None and _aware(r.absolute_expires_at) <= now:
                    continue
                s.expunge(r)
                out.append(r)
            return out


# ── Request-context helpers (called from routes) ─────────────────────────────

def current_uid():
    return getattr(g, "uid", None)


def current_session():
    return getattr(g, "session_row", None)


def gate_authenticated() -> bool:
    """Passcode-gate flag from the server-side session (never client data)."""
    row = current_session()
    return bool(row is not None and (row.flags or {}).get("gate"))


def _set_pending_cookies(raw: str | None, csrf: str | None, delete: bool = False,
                         remember: bool = False, max_age: int | None = None) -> None:
    g._set_sid = (raw, delete, remember, max_age)
    if csrf is not None:
        g._set_csrf = (csrf, delete)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def login_session(uid: int, remember: bool = False) -> None:
    """Rotate the session identifier at an authentication boundary (WS03-02).

    The old identifier is revoked immediately; a fresh id + CSRF token are set
    on the response. The passcode-gate flag carries over if present.
    """
    from flask import current_app

    store = current_app.config["SESSIONS"]
    cfg = current_app.config["APP_CONFIG"]
    old = current_session()
    old_flags = dict(old.flags) if old is not None and old.flags else {}
    if old is not None:
        store.revoke(getattr(g, "sid_raw", "") or "")
    idle_min = cfg.REMEMBER_DAYS * 24 * 60 if remember else cfg.SESSION_TIMEOUT_MIN
    absolute_min = cfg.REMEMBER_DAYS * 24 * 60 if remember else cfg.SESSION_ABSOLUTE_HOURS * 60
    raw, row = store.create(
        user_id=uid, csrf_token=new_csrf_token(), remember=bool(remember),
        device=(request.headers.get("User-Agent") or "")[:200],
        ip_hash=hash_ip(request.remote_addr), flags=old_flags,
        idle_min=idle_min, absolute_min=absolute_min,
    )
    g.session_row = row
    g.sid_raw = raw
    max_age = cfg.REMEMBER_DAYS * 24 * 3600 if remember else None
    _set_pending_cookies(raw, row.csrf_token, remember=remember, max_age=max_age)


def clear_session() -> None:
    """Logout: invalidate the server row and drop both cookies."""
    from flask import current_app

    store = current_app.config["SESSIONS"]
    if getattr(g, "sid_raw", None):
        store.revoke(g.sid_raw)
    g.session_row = None
    g.uid = None
    _set_pending_cookies(None, None, delete=True)


def grant_gate() -> None:
    """Mark the current session passcode-gate-authenticated (creates an
    anonymous server-side session when none exists)."""
    from flask import current_app

    store = current_app.config["SESSIONS"]
    cfg = current_app.config["APP_CONFIG"]
    row = current_session()
    if row is not None:
        flags = dict(row.flags or {})
        flags["gate"] = True
        store.set_flags(row.id, flags)
        row.flags = flags
        return
    raw, row = store.create(
        user_id=None, csrf_token=new_csrf_token(), remember=False,
        device=(request.headers.get("User-Agent") or "")[:200],
        ip_hash=hash_ip(request.remote_addr), flags={"gate": True},
        idle_min=cfg.SESSION_TIMEOUT_MIN, absolute_min=cfg.SESSION_ABSOLUTE_HOURS * 60,
    )
    g.session_row = row
    g.sid_raw = raw
    _set_pending_cookies(raw, row.csrf_token)


def stamp_admin_reauth() -> None:
    """Record a successful admin reauthentication on the current session."""
    from flask import current_app

    store = current_app.config["SESSIONS"]
    row = current_session()
    if row is None:
        return
    flags = dict(row.flags or {})
    flags["reauth_at"] = _now().isoformat()
    store.set_flags(row.id, flags)
    row.flags = flags


def reauth_age_seconds() -> float | None:
    row = current_session()
    if row is None:
        return None
    iso = (row.flags or {}).get("reauth_at")
    if not iso:
        return None
    try:
        then = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
    return (_now() - then).total_seconds()


# ── App wiring ───────────────────────────────────────────────────────────────

def init_session_security(app, store: SessionStore, cfg) -> None:
    """Register the request lifecycle hooks. Must run BEFORE the passcode gate
    and any route that reads current_uid()."""
    from flask import current_app

    # Paths that must not answer SESSION_EXPIRED (pre-auth / health surfaces).
    open_paths = {
        "/api/health", "/api/health/ready", "/api/auth/status", "/api/auth/login",
        "/api/auth/logout", "/api/account/login", "/api/account/register",
        "/api/account/logout", "/api/account/forgot", "/api/account/reset",
        "/api/account/google", "/api/account/verify",
    }

    def _allowed_origins() -> set[str]:
        import urllib.parse as up

        origins = set()
        for raw_url in (cfg.APP_BASE_URL, *cfg.CORS_ORIGINS):
            try:
                netloc = up.urlparse(raw_url or "").netloc
            except ValueError:
                continue
            if netloc:
                origins.add(netloc.lower())
        if request.host:
            origins.add(request.host.lower())  # same-origin requests
        return origins

    def _origin_netloc(value: str) -> str | None:
        import urllib.parse as up

        try:
            parsed = up.urlparse(value or "")
        except ValueError:
            return None
        return parsed.netloc.lower() or None

    @app.before_request
    def _load_session():
        from flask import current_app as ca

        g.uid = None
        g.session_row = None
        g.sid_raw = None
        g._set_sid = None
        g._set_csrf = None
        raw = request.cookies.get(COOKIE_NAME)
        if not raw:
            return None
        row, status = store.get(raw)
        if status != "ok":
            g._set_sid = (None, True, False, 0)  # drop the dead cookie
            if status == "expired":
                g.session_expired = True
            return None
        # Server-side idle expiry (WS03-01).
        idle_min = (cfg.REMEMBER_DAYS * 24 * 60) if row.remember else cfg.SESSION_TIMEOUT_MIN
        last = _aware(row.last_seen_at)
        idle = (_now() - last).total_seconds() / 60.0 if last else 0.0
        if idle > idle_min:
            store.revoke(raw)
            g._set_sid = (None, True, False, 0)
            g.session_expired = True
            return None
        store.touch(row.id)
        g.session_row = row
        g.sid_raw = raw
        g.uid = row.user_id
        return None

    @app.before_request
    def _session_expired_guard():
        if not getattr(g, "session_expired", False):
            return None
        if request.path.startswith("/api/") and request.path not in open_paths:
            from app.errors import ApiError, error_response

            return error_response(
                ApiError("SESSION_EXPIRED", "Session expired — please sign in again", 401)
            )
        return None

    @app.before_request
    def _csrf_protect():
        """WS03-03 — all unsafe /api/* requests: reject cross-site origins;
        authenticated requests additionally double-submit the CSRF token."""
        if request.method not in _UNSAFE or not request.path.startswith("/api/"):
            return None
        from app.errors import ApiError, error_response

        origin_header = request.headers.get("Origin") or request.headers.get("Referer")
        if origin_header:
            netloc = _origin_netloc(origin_header)
            if not netloc or netloc not in _allowed_origins():
                return error_response(
                    ApiError("CSRF_REJECTED", "Cross-site request rejected", 403)
                )
        row = current_session()
        if row is not None:
            given = request.headers.get(CSRF_HEADER) or ""
            if not given or not hmac.compare_digest(given, row.csrf_token):
                return error_response(
                    ApiError("CSRF_REJECTED", "Missing or invalid CSRF token", 403)
                )
        return None

    @app.after_request
    def _apply_session_cookies(resp):
        pending = getattr(g, "_set_sid", None)
        if pending is not None:
            raw, delete, remember, max_age = pending
            if delete:
                resp.delete_cookie(COOKIE_NAME, httponly=True,
                                   samesite=cfg.COOKIE_SAMESITE, secure=cfg.COOKIE_SECURE)
            elif raw:
                resp.set_cookie(
                    COOKIE_NAME, raw,
                    max_age=max_age, httponly=True,
                    samesite=cfg.COOKIE_SAMESITE, secure=cfg.COOKIE_SECURE,
                )
        # Keep the JS-readable CSRF cookie in sync with the server row.
        row = current_session()
        csrf_pending = getattr(g, "_set_csrf", None)
        if csrf_pending is not None:
            csrf, delete = csrf_pending
            if delete:
                resp.delete_cookie(CSRF_COOKIE, samesite=cfg.COOKIE_SAMESITE,
                                   secure=cfg.COOKIE_SECURE)
            else:
                resp.set_cookie(CSRF_COOKIE, csrf, max_age=60 * 60 * 24 * 30,
                                httponly=False, samesite=cfg.COOKIE_SAMESITE,
                                secure=cfg.COOKIE_SECURE)
        elif row is not None:
            resp.set_cookie(CSRF_COOKIE, row.csrf_token, max_age=60 * 60 * 24 * 30,
                            httponly=False, samesite=cfg.COOKIE_SAMESITE,
                            secure=cfg.COOKIE_SECURE)
        return resp


class CsrfAwareClient(_WerkzeugClient):
    """Test client that mirrors the SPA: reads the ar_csrf cookie and echoes it
    in X-CSRF-Token on unsafe API requests. Dedicated CSRF tests use a raw
    FlaskClient to prove enforcement instead."""

    def _csrf_from_jar(self) -> str | None:
        getter = getattr(self, "get_cookie", None)
        if getter is None:  # pragma: no cover - very old werkzeug
            return None
        cookie = getter(CSRF_COOKIE)
        return cookie.value if cookie is not None else None

    def open(self, *args, **kwargs):  # noqa: D102
        method = (kwargs.get("method") or "GET").upper()
        path = args[0] if args else kwargs.get("path", "")
        if method in _UNSAFE and str(path).startswith("/api/"):
            token = self._csrf_from_jar()
            if token:
                headers = dict(kwargs.pop("headers", None) or {})
                headers[CSRF_HEADER] = token
                kwargs["headers"] = headers
        return super().open(*args, **kwargs)

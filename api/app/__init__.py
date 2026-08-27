from flask import Flask, request
from flask_cors import CORS
from .config import Config
from .errors import register_error_handlers, error_response, request_id, ApiError
from . import session as auth_session  # submodule (not flask's session)


def create_app(overrides=None):
    app = Flask(__name__)
    overrides = overrides or {}
    cfg = Config(overrides)

    # ── Fail-closed: never boot a real deployment with the built-in dev secret ──
    # The secret_key signs cookies; a known value would let an attacker forge
    # sessions. Tests pass TESTING=True and are exempt.
    if not cfg.TESTING and cfg.SESSION_SECRET == "dev-secret-change-me":
        raise RuntimeError(
            "SESSION_SECRET is unset (using the insecure default). Set a strong, "
            "random SESSION_SECRET (e.g. `python -c \"import secrets;print(secrets.token_urlsafe(48))\"`) "
            "before starting the app."
        )

    # ── WS03-06B: fail closed when email flows are enabled without a provider ─
    # (Account recovery/verification must never silently fall back to logging
    # links.) Checked before any infrastructure init: startup must fail fast.
    if not cfg.TESTING and (cfg.EMAIL_VERIFICATION_REQUIRED or cfg.FAIL_CLOSED_ON_MAIL):
        from .services import mailer

        if not mailer.delivery_configured(cfg):
            raise RuntimeError(
                "Email-dependent account flows are enabled "
                "(EMAIL_VERIFICATION_REQUIRED / FAIL_CLOSED_ON_MAIL) but SMTP is not "
                "configured. Configure SMTP_* or disable the features; the app "
                "refuses to start rather than silently dropping account email."
            )

    # ── WS08-04B: production database configuration invariants ─────────────
    # Convenience defaults (ielts/ielts, SQLite) are acceptable ONLY for
    # disposable local development. A production-marked deployment must never
    # boot with them; this fails closed before any infrastructure init.
    if not cfg.TESTING and cfg.APP_ENV == "production":
        url = (cfg.DATABASE_URL or "").strip()
        lowered = url.lower()
        if "ielts:ielts@" in lowered or "change-me-strong@" in lowered:
            raise RuntimeError(
                "WS08-04B: DATABASE_URL uses known development/default credentials. "
                "Set strong POSTGRES_* credentials and a matching DATABASE_URL "
                "(ideally the least-privilege runtime role) before production boot."
            )
        if not lowered.startswith("postgresql"):
            raise RuntimeError(
                "WS08-04B: production requires PostgreSQL via DATABASE_URL "
                "(postgresql://...); refusing to start on this backend."
            )

    # ── WS09-02: a TLS (COOKIE_SECURE) deployment must pin its Host allow-list,
    # otherwise host-header injection stays open. Fail the boot instead.
    if not cfg.TESTING and cfg.COOKIE_SECURE and not cfg.TRUSTED_HOSTS:
        raise RuntimeError(
            "COOKIE_SECURE=1 (production TLS) requires TRUSTED_HOSTS to be set "
            "(comma-separated public hostnames). Refusing to start without an "
            "explicit Host allow-list (WS09-02)."
        )

    app.config["APP_CONFIG"] = cfg
    app.secret_key = cfg.SESSION_SECRET
    # Session-cookie hardening: HttpOnly (no JS access), SameSite (CSRF defence),
    # Secure (HTTPS-only) when configured for a TLS deployment.
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE=cfg.COOKIE_SAMESITE,
        SESSION_COOKIE_SECURE=cfg.COOKIE_SECURE,
    )
    # Cap request bodies to blunt memory-exhaustion DoS (returns 413).
    app.config["MAX_CONTENT_LENGTH"] = cfg.MAX_CONTENT_BYTES

    # ── WS09-03: ProxyFix only for the exact trusted proxy topology ───────────
    # Applied ONLY when TRUSTED_PROXIES > 0 (production: nginx → gunicorn = 1).
    # It rewrites remote_addr from the proxy-set X-Forwarded-For chain (so rate
    # limits key the real client IP) and optionally scheme from X-Forwarded-Proto.
    # X-Forwarded-Host is never honored, and with TRUSTED_PROXIES=0 no forwarded
    # header is trusted at all — a direct client cannot spoof its IP.
    if cfg.TRUSTED_PROXIES > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=cfg.TRUSTED_PROXIES,
            x_proto=1 if cfg.TRUSTED_PROXY_PROTO else 0,
            x_host=0,
            x_port=0,
        )

    # ── WS09-04: CORS is opt-in and exact ─────────────────────────────────────
    # Same-origin production (nginx serves the SPA and proxies /api) needs no
    # cross-origin browser access, so CORS is fully ABSENT unless explicitly
    # configured. Never wildcard-with-credentials.
    if cfg.CORS_ORIGINS:
        CORS(
            app,
            origins=list(cfg.CORS_ORIGINS),
            supports_credentials=True,
            allow_headers=["Content-Type", "X-CSRF-Token", "X-Lang", "X-Request-ID"],
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            max_age=600,
        )
    register_error_handlers(app)

    # ── WS10: structured logging + request telemetry + metrics ───────────────
    # Consumes WS09's X-Request-ID correlation. Never sees request bodies.
    from .observability import init_observability
    init_observability(app, cfg)

    # ── WS09-02: trusted-host validation (fail closed) ────────────────────────
    # When TRUSTED_HOSTS is configured, any request whose Host header is not on
    # the allow-list is rejected before any other work. This kills host-header
    # injection (cache poisoning / link rewrite). Production TLS deployments are
    # also required to set it (boot guard below).
    _trusted_hosts = cfg.TRUSTED_HOSTS

    @app.before_request
    def _require_trusted_host():
        if not _trusted_hosts or request.method == "OPTIONS":
            return None
        # Loopback peers are local health probes (the API port is not publicly
        # reachable in production), not client traffic — exempt them.
        if (request.remote_addr or "") in ("127.0.0.1", "::1"):
            return None
        host = (request.host or "").split(":", 1)[0].strip().lower()
        if host not in _trusted_hosts:
            return error_response(ApiError(
                "UNTRUSTED_HOST", "Request host is not recognized", 421))
        return None

    # ── Dependency injection ───────────────────────────────────────────────
    if "REPO" in overrides and "GATEWAY" in overrides:
        # Test path: use injected instances directly; do NOT init a real engine.
        app.config["REPO"] = overrides["REPO"]
        app.config["GATEWAY"] = overrides["GATEWAY"]
        session_factory = getattr(overrides["REPO"], "session_factory", None)
    elif cfg.DATABASE_URL:
        # Production path: init engine, seed, build repo + gateway.
        from sqlalchemy.orm import sessionmaker
        from .data.db import init_engine
        from .data.repositories import Repository
        from .data.seed import seed_all
        from .services.llm import LlmGateway

        # Schema is owned by Alembic migrations (Dockerfile runs `alembic upgrade
        # head` before the app starts). No create_all here, so incremental
        # migrations can ALTER existing tables without data loss.
        engine = init_engine(cfg.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        seed_all(Session)
        app.config["REPO"] = Repository(Session)
        app.config["GATEWAY"] = LlmGateway(cfg)
        session_factory = Session
    else:
        session_factory = None
    # else: no DATABASE_URL and no injected deps → health-test path; REPO/GATEWAY
    # remain unset. Routes that need them will KeyError, but health doesn't.

    # ── WS07: job service + AI concurrency guard ─────────────────────────────
    # Job records/dispatch: Celery+Redis when REDIS_URL is set (public
    # production), synchronous inline execution otherwise (offline dev keeps
    # today's behaviour). Concurrency guard bounds active heavy AI ops/user.
    if "REPO" in app.config:
        from .jobs.service import JobService
        from .costguard import ConcurrencyLimiter

        _redis_client = overrides.get("REDIS")
        if _redis_client is None and cfg.REDIS_URL:
            from .ratelimit import build_redis_client
            try:
                _redis_client = build_redis_client(cfg.REDIS_URL)
            except Exception:
                _redis_client = None
        app.config["JOBS"] = JobService(
            app.config["REPO"], cfg,
            gateway=app.config.get("GATEWAY"),
            dispatcher=overrides.get("JOBS_DISPATCH"),
            redis_client=_redis_client,
        )
        app.config["CONCURRENCY"] = ConcurrencyLimiter(_redis_client)

    # ── WS03-01/02/03: server-side sessions + CSRF + rotation ────────────────
    if session_factory is not None:
        from .session import SessionStore, init_session_security, CsrfAwareClient

        app.config["SESSIONS"] = SessionStore(session_factory)
        init_session_security(app, app.config["SESSIONS"], cfg)
        # Mirrors the SPA contract (cookie -> X-CSRF-Token) for the whole suite.
        app.test_client_class = CsrfAwareClient

    # ── WS03-08: shared-store abuse counters (Redis when configured) ─────────
    from .kv import build_kv

    app.config["KV"] = overrides.get("KV") or build_kv(cfg.REDIS_URL)

    # ── Rate limiting (WS07-01/02/09) ─────────────────────────────────────────
    # Dimension-aware limiter: Redis-backed shared windows when REDIS_URL is
    # set (public production — every replica enforces the SAME effective limit,
    # WS07-01 required test), else the documented in-process fallback for
    # single-worker self-hosting. Guards credential brute-force and unauth LLM
    # cost-abuse; signed-in heavy usage is keyed by USER ID, never IP alone.
    # Disabled under TESTING so the suite can hammer endpoints (set
    # RATE_LIMIT_TEST_FORCE to exercise the limiter inside tests).
    # (WS03-08 additionally enforces shared-store per-account throttles inside
    # the auth flows themselves.)
    if cfg.RATE_LIMIT_ENABLED and (not cfg.TESTING or cfg.RATE_LIMIT_TEST_FORCE):
        from .ratelimit import (
            InProcessBackend, RateLimitService, RedisBackend, build_redis_client,
            client_key, rule_for,
        )
        _rl_backend = None
        if "RATE_LIMIT_REDIS" in overrides:
            _rl_backend = RedisBackend(overrides["RATE_LIMIT_REDIS"])
        elif cfg.REDIS_URL:
            try:
                _rl_backend = RedisBackend(build_redis_client(cfg.REDIS_URL))
            except Exception:
                _rl_backend = None  # redis lib unavailable locally → fallback
        if _rl_backend is None:
            _rl_backend = InProcessBackend()
        limiter = RateLimitService(
            _rl_backend,
            fail_closed=cfg.RATE_LIMIT_FAIL_CLOSED,
            escalate_after=cfg.RATE_LIMIT_ESCALATE_AFTER,
        )

        @app.before_request
        def _rate_limit():
            if request.method == "OPTIONS" or not request.path.startswith("/api/"):
                return None
            rule = rule_for(request.path)
            email = None
            if rule.kind == "credential":
                email = (request.get_json(silent=True) or {}).get("email")
            verdict = limiter.allow(
                rule,
                ip=client_key(request.remote_addr),
                user_id=auth_session.current_uid(),
                email=email,
            )
            if not verdict.allowed:
                if verdict.unavailable:
                    # Redis configured but unreachable: fail closed, retryable.
                    resp = error_response(ApiError(
                        "RATE_LIMITER_UNAVAILABLE",
                        "Security limits are briefly unavailable — please retry",
                        503,
                    ))
                else:
                    resp = error_response(ApiError(
                        "RATE_LIMITED",
                        "Too many requests — please slow down and try again shortly",
                        429,
                    ))
                if verdict.retry_after:
                    resp[0].headers["Retry-After"] = str(verdict.retry_after)
                return resp
            return None

    # ── Security response headers ──────────────────────────────────────────────
    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        # API returns JSON only; deny all embedding/exec for this origin.
        resp.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        # WS09-05: authenticated API responses must never be cached by shared
        # intermediaries or the browser back/forward cache.
        if request.path.startswith("/api/"):
            resp.headers.setdefault("Cache-Control", "no-store")
        # WS09-08: correlation id on every response (echoed in error bodies).
        resp.headers["X-Request-ID"] = request_id()
        return resp

    # ── Passcode gate (no-op when APP_PASSCODE is empty) ─────────────────────
    # The passcode grant lives in the server-side session (revocable), not a
    # client-side signed cookie.
    _OPEN_PATHS = {"/api/health", "/api/health/ready", "/api/auth/status", "/api/auth/login",
                   "/api/auth/logout", "/api/internal/reminders/run"}

    @app.before_request
    def _require_passcode():
        if not cfg.APP_PASSCODE:
            return None
        path = request.path
        if not path.startswith("/api/") or path in _OPEN_PATHS:
            return None
        if request.method == "OPTIONS":  # CORS preflight
            return None
        if not auth_session.gate_authenticated():
            return error_response(ApiError("UNAUTHORIZED", "Passcode required", 401))
        return None

    # ── WS03-05: email-ownership gate on expensive/persistent features ───────
    # Central (path-based) on purpose: LLM-cost routes stay protected even as
    # new route modules are added. Only active when EMAIL_VERIFICATION_REQUIRED.
    _EXPENSIVE_PREFIXES = (
        "/api/writing/evaluate", "/api/speaking/evaluate", "/api/speaking/roleplay",
        "/api/speaking/transcribe", "/api/reading/generate", "/api/listening/generate",
        "/api/lesson/generate", "/api/vocab", "/api/pronounce/",
    )

    @app.before_request
    def _require_verified_email():
        if not cfg.EMAIL_VERIFICATION_REQUIRED or not request.path.startswith("/api/"):
            return None
        if request.method == "OPTIONS":
            return None
        if not any(request.path.startswith(p) for p in _EXPENSIVE_PREFIXES):
            return None
        uid = auth_session.current_uid()
        if uid is None:
            return None  # anonymous flows are handled by the passcode/auth gate
        repo = app.config.get("REPO")
        if repo is None:
            return None
        u = repo.get_user_by_id(uid)
        if u is None or u.email_verified:
            return None
        from app.routes.admin import _is_admin_email

        if _is_admin_email(u.email):
            return None
        return error_response(
            ApiError("EMAIL_UNVERIFIED",
                     "Verify your email address to use this feature", 403)
        )

    # ── Blueprints ─────────────────────────────────────────────────────────
    from .routes.health import bp as health_bp
    from .routes.onboarding import bp as onboarding_bp
    from .routes.placement import bp as placement_bp
    from .routes.skills import bp as skills_bp
    from .routes.practice import bp as practice_bp
    from .routes.program import bp as program_bp
    from .routes.tips import bp as tips_bp
    from .routes.reading import bp as reading_bp
    from .routes.listening import bp as listening_bp
    from .routes.writing import bp as writing_bp
    from .routes.speaking import bp as speaking_bp
    from .routes.history import bp as history_bp
    from .routes.lesson import bp as lesson_bp
    from .routes.mocks import bp as mocks_bp
    from .routes.pronounce import bp as pronounce_bp
    from .routes.cards import bp as cards_bp
    from .routes.vocab import bp as vocab_bp
    from .routes.auth import bp as auth_bp
    from .routes.account import bp as account_bp
    from .routes.admin import bp as admin_bp
    from .routes.feedback import bp as gate_bp
    from .routes.internal import bp as internal_bp
    from .routes.jobs import bp as jobs_bp
    from .routes.analytics import bp as analytics_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(placement_bp)
    app.register_blueprint(skills_bp)
    app.register_blueprint(practice_bp)
    app.register_blueprint(program_bp)
    app.register_blueprint(tips_bp)
    app.register_blueprint(reading_bp)
    app.register_blueprint(listening_bp)
    app.register_blueprint(writing_bp)
    app.register_blueprint(speaking_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(lesson_bp)
    app.register_blueprint(mocks_bp)
    app.register_blueprint(pronounce_bp)
    app.register_blueprint(cards_bp)
    app.register_blueprint(vocab_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(gate_bp)
    app.register_blueprint(internal_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(analytics_bp)

    return app

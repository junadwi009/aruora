from flask import Flask, request
from flask_cors import CORS
from .config import Config
from .errors import register_error_handlers, error_response, ApiError
from . import session as auth_session  # submodule (not flask's session)


def create_app(overrides=None):
    app = Flask(__name__)
    overrides = overrides or {}
    cfg = Config(overrides)
    app.config["APP_CONFIG"] = cfg
    app.secret_key = cfg.SESSION_SECRET

    # supports_credentials so the passcode session cookie works cross-origin (dev).
    CORS(app, origins=[cfg.CORS_ORIGIN], supports_credentials=True)
    register_error_handlers(app)

    # ── Sliding session timeout (Phase 3a) ─────────────────────────────────────
    from datetime import datetime

    _TIMEOUT_OPEN = {
        "/api/health", "/api/auth/status", "/api/auth/login", "/api/auth/logout",
        "/api/account/login", "/api/account/register", "/api/account/logout",
        "/api/account/forgot", "/api/account/reset",
    }

    @app.before_request
    def _session_timeout():
        from flask import session as flask_session
        last = flask_session.get("last_seen")
        if not last:
            return None
        try:
            last_dt = datetime.fromisoformat(last)
        except (TypeError, ValueError):
            return None
        idle_min = (auth_session._now() - last_dt).total_seconds() / 60.0
        if idle_min > cfg.SESSION_TIMEOUT_MIN:
            flask_session.clear()
            if request.path.startswith("/api/") and request.path not in _TIMEOUT_OPEN:
                return error_response(ApiError("SESSION_EXPIRED", "Session expired — please sign in again", 401))
            return None
        flask_session["last_seen"] = auth_session._now().isoformat()
        return None

    # ── Passcode gate (no-op when APP_PASSCODE is empty) ───────────────────────
    _OPEN_PATHS = {"/api/health", "/api/auth/status", "/api/auth/login", "/api/auth/logout",
                   "/api/internal/reminders/run"}

    @app.before_request
    def _require_passcode():
        from flask import session as flask_session
        if not cfg.APP_PASSCODE:
            return None
        path = request.path
        if not path.startswith("/api/") or path in _OPEN_PATHS:
            return None
        if request.method == "OPTIONS":  # CORS preflight
            return None
        if not flask_session.get("auth"):
            return error_response(ApiError("UNAUTHORIZED", "Passcode required", 401))
        return None

    # ── Dependency injection ───────────────────────────────────────────────
    if "REPO" in overrides and "GATEWAY" in overrides:
        # Test path: use injected instances directly; do NOT init a real engine.
        app.config["REPO"] = overrides["REPO"]
        app.config["GATEWAY"] = overrides["GATEWAY"]
    elif cfg.DATABASE_URL:
        # Production path: init engine, seed, build repo + gateway.
        from sqlalchemy.orm import sessionmaker
        from .data.db import init_engine
        from .data.models import Base
        from .data.repositories import Repository
        from .data.seed import seed_all
        from .services.llm import LlmGateway

        engine = init_engine(cfg.DATABASE_URL)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        seed_all(Session)
        app.config["REPO"] = Repository(Session)
        app.config["GATEWAY"] = LlmGateway(cfg)
    # else: no DATABASE_URL and no injected deps → health-test path; REPO/GATEWAY
    # remain unset. Routes that need them will KeyError, but health doesn't.

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
    from .routes.internal import bp as internal_bp

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
    app.register_blueprint(internal_bp)

    return app

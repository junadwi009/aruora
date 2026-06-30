from flask import Flask
from flask_cors import CORS
from .config import Config
from .errors import register_error_handlers


def create_app(overrides=None):
    app = Flask(__name__)
    overrides = overrides or {}
    cfg = Config(overrides)
    app.config["APP_CONFIG"] = cfg

    CORS(app, origins=[cfg.CORS_ORIGIN])
    register_error_handlers(app)

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

    return app

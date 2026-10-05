"""Separated liveness, dependency readiness and admin-only diagnostics."""
from flask import Blueprint, current_app, jsonify
from app.services.asr import asr_ready

bp = Blueprint("health", __name__)


@bp.get("/api/health")
def health():
    """Public client configuration; never expose infrastructure or secrets."""
    cfg = current_app.config["APP_CONFIG"]
    return jsonify({
        "ok": True,
        "asrReady": asr_ready(cfg),
        "googleClientId": cfg.GOOGLE_CLIENT_ID,
    })


@bp.get("/api/health/ready")
def ready():
    """Fail closed when a configured dependency is unavailable."""
    checks = {"db": False, "redis": True}
    repo = current_app.config.get("REPO")
    if repo is not None:
        try:
            sf = getattr(repo, "session_factory", None)
            if sf is not None:
                from sqlalchemy import text
                with sf() as s:
                    s.execute(text("SELECT 1"))
            checks["db"] = True
        except Exception:
            checks["db"] = False

    cfg = current_app.config["APP_CONFIG"]
    if cfg.REDIS_URL:
        checks["redis"] = False
        try:
            # This blueprint lives under app.routes, not directly under app.
            from app.ratelimit import build_redis_client
            checks["redis"] = bool(build_redis_client(cfg.REDIS_URL).ping())
        except Exception:
            checks["redis"] = False

    ok = all(checks.values())
    return jsonify({"ok": ok, "checks": checks}), (200 if ok else 503)


@bp.get("/api/admin/health/detail")
def health_detail():
    from app.routes.admin import _require_admin
    _require_admin()
    cfg = current_app.config["APP_CONFIG"]
    return jsonify({
        "llmMode": cfg.LLM_MODE,
        "providerConfigured": cfg.provider_configured,
        "asrReady": asr_ready(cfg),
        "jobsQueued": cfg.jobs_queued,
    }), 200

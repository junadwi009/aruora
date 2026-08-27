"""WS09-10 — separated health surfaces.

- GET /api/health          liveness + public client config (no topology).
- GET /api/health/ready    readiness: DB / required shared services only,
                           expressed as booleans — never URLs, hosts or keys.
- GET /api/admin/health/detail  detailed diagnostics, admin-only (provider
                           mode, model config presence, ASR probe, queue mode).
"""
from flask import Blueprint, current_app, jsonify

from app.services.asr import asr_ready

bp = Blueprint("health", __name__)


@bp.get("/api/health")
def health():
    """Liveness + the two values the anonymous SPA legitimately needs:
    the PUBLIC Google OAuth client id (embedded in the web bundle anyway)
    and whether speech recording can expect transcription."""
    cfg = current_app.config["APP_CONFIG"]
    return jsonify({
        "ok": True,
        "asrReady": asr_ready(cfg),
        "googleClientId": cfg.GOOGLE_CLIENT_ID,
    })


@bp.get("/api/health/ready")
def ready():
    """Readiness for orchestrators/load balancers: can this process serve?
    Every check is reported as a boolean; nothing about internal topology
    (hosts, ports, URLs) is disclosed. 503 when any configured dependency is
    unavailable so traffic is drained BEFORE learners hit failures."""
    checks = {"db": False, "redis": True}  # redis only checked when configured
    repo = current_app.config.get("REPO")
    if repo is not None:
        try:
            sf = getattr(repo, "session_factory", None)
            if sf is not None:
                from sqlalchemy import text

                with sf() as s:
                    s.execute(text("SELECT 1"))
                checks["db"] = True
            else:
                checks["db"] = True  # non-SQL repo (test fakes) — treat as up
        except Exception:  # noqa: BLE001 — readiness must not leak internals
            checks["db"] = False

    cfg = current_app.config["APP_CONFIG"]
    if cfg.REDIS_URL:
        checks["redis"] = False
        try:
            from .ratelimit import build_redis_client

            build_redis_client(cfg.REDIS_URL).ping()
            checks["redis"] = True
        except Exception:  # noqa: BLE001
            checks["redis"] = False

    ok = all(bool(v) for v in checks.values())
    return jsonify({"ok": ok, "checks": checks}), (200 if ok else 503)


@bp.get("/api/admin/health/detail")
def health_detail():
    """Diagnostics for operators: authenticated admin only (WS09-10)."""
    from app.routes.admin import _require_admin

    _require_admin()
    cfg = current_app.config["APP_CONFIG"]
    return jsonify({
        "llmMode": cfg.LLM_MODE,
        "providerConfigured": cfg.provider_configured,
        "asrReady": asr_ready(cfg),
        "jobsQueued": cfg.jobs_queued,
    }), 200

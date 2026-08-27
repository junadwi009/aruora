"""
Phase 4a — cron-triggered study reminders. An external scheduler (cron / the
deploy platform) POSTs hourly with the X-Reminder-Token header; this sends a
reminder email to every user whose reminder hour matches and who hasn't been
emailed today. SMTP-optional (dev logs the message).

Protect publicly: set REMINDER_TOKEN. Empty token = endpoint disabled (401).
"""
import hmac
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _repo, _cfg
from app.services import mailer

bp = Blueprint("internal", __name__)


@bp.post("/api/internal/reminders/run")
def run_reminders():
    cfg = _cfg()
    token = cfg.REMINDER_TOKEN
    given = request.headers.get("X-Reminder-Token") or ""
    if not token or not hmac.compare_digest(str(given), str(token)):  # constant-time
        raise ApiError("UNAUTHORIZED", "Invalid reminder token", 401)

    # Current UTC instant; ?now=<iso> overrides it (for testing / replays).
    now = datetime.now(timezone.utc)
    now_arg = request.args.get("now")
    if now_arg:
        now = datetime.fromisoformat(now_arg)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

    repo = _repo()
    sent = 0
    # Each due user carries its own local `date` (timezones differ), so mark 'sent'
    # against that user's calendar day.
    for u in repo.due_reminders(now, cfg.REMINDER_DEFAULT_TZ):
        ok = mailer.send_email(
            cfg, u["email"], "Your ARUORA IELTS study reminder",
            f"Hi {u['name'] or 'there'}, time for today's practice. "
            f"Open {cfg.APP_BASE_URL} and keep your streak alive!",
        )
        # Mark sent regardless of SMTP delivery so dev (no SMTP) doesn't loop.
        repo.mark_reminder_sent(u["id"], u["date"])
        sent += 1
        _ = ok
    return jsonify({"sent": sent}), 200


@bp.post("/api/internal/maintenance/run")
def run_maintenance():
    """WS08-08 — manual/ops trigger for the data-lifecycle sweep (the same
    sweep the worker-beat schedule runs hourly). Guarded by its own shared
    secret; empty MAINTENANCE_TOKEN = endpoint disabled (fail closed)."""
    import hmac as _hmac

    from app.jobs.maintenance import run_maintenance as _sweep

    cfg = _cfg()
    token = cfg.MAINTENANCE_TOKEN
    given = request.headers.get("X-Maintenance-Token") or ""
    if not token or not _hmac.compare_digest(str(given), str(token)):
        raise ApiError("UNAUTHORIZED", "Invalid maintenance token", 401)
    counts = _sweep(_repo(), cfg)
    # Counts only — no learner content, no identifiers.
    return jsonify({"ok": True, "purged": counts}), 200

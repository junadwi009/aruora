"""
Phase 4a — cron-triggered study reminders. An external scheduler (cron / the
deploy platform) POSTs hourly with the X-Reminder-Token header; this sends a
reminder email to every user whose reminder hour matches and who hasn't been
emailed today. SMTP-optional (dev logs the message).

Protect publicly: set REMINDER_TOKEN. Empty token = endpoint disabled (401).
"""
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
    if not token or request.headers.get("X-Reminder-Token") != token:
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
            cfg, u["email"], "Your IELTS Coach study reminder",
            f"Hi {u['name'] or 'there'}, time for today's practice. "
            f"Open {cfg.APP_BASE_URL} and keep your streak alive!",
        )
        # Mark sent regardless of SMTP delivery so dev (no SMTP) doesn't loop.
        repo.mark_reminder_sent(u["id"], u["date"])
        sent += 1
        _ = ok
    return jsonify({"sent": sent}), 200

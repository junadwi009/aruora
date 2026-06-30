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

    now = datetime.now(timezone.utc)
    hour = int(request.args.get("hour", now.hour))
    today = request.args.get("today", now.date().isoformat())

    repo = _repo()
    sent = 0
    for u in repo.due_reminders(hour, today):
        ok = mailer.send_email(
            cfg, u["email"], "Your IELTS Coach study reminder",
            f"Hi {u['name'] or 'there'}, time for today's practice. "
            f"Open {cfg.APP_BASE_URL} and keep your streak alive!",
        )
        # Mark sent regardless of SMTP delivery so dev (no SMTP) doesn't loop.
        repo.mark_reminder_sent(u["id"], today)
        sent += 1
        _ = ok
    return jsonify({"sent": sent}), 200

"""
SMTP-optional mailer. When SMTP is configured (SMTP_HOST set) it sends real
email; otherwise it logs the message (dev) and returns False so callers know it
wasn't delivered. No new dependency — uses the stdlib smtplib.
"""
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_email(cfg, to: str, subject: str, body: str) -> bool:
    if not getattr(cfg, "SMTP_HOST", ""):
        # No SMTP in dev — surface the message (incl. any reset link) at WARNING
        # so it's visible in the server log. Configure SMTP_* for real delivery.
        logger.warning(
            "EMAIL (no SMTP configured — not sent) to=%s subject=%s\n%s",
            to, subject, body,
        )
        return False
    msg = EmailMessage()
    msg["From"] = cfg.SMTP_FROM or cfg.SMTP_USER or "no-reply@ielts.local"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT, timeout=15) as s:
            if cfg.SMTP_USER:
                s.starttls()
                s.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
            s.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001 — never crash the request on mail failure
        logger.warning("EMAIL send failed to=%s: %s", to, exc)
        return False

"""SMTP-optional mailer (WS03-06B hardened).

Sends account email via SMTP when configured; otherwise reports not-delivered.
NEVER logs email bodies, reset/verification URLs, tokens, or full recipient
addresses — only delivery metadata (outcome, latency, privacy-safe recipient
reference). A missing provider in production is a startup failure enforced by
FAIL_CLOSED_ON_MAIL, never a silent log-and-continue fallback.
"""
import hashlib
import logging
import smtplib
import time
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def delivery_configured(cfg) -> bool:
    """True when SMTP delivery is actually configured."""
    return bool(getattr(cfg, "SMTP_HOST", ""))


def recipient_ref(to: str) -> str:
    """Privacy-safe recipient reference for logs (no raw email address)."""
    return hashlib.sha256((to or "").strip().lower().encode()).hexdigest()[:12]


def send_email(cfg, to: str, subject: str, body: str) -> bool:
    """Deliver `body` to `to`. Returns True only when the provider accepted it.

    Logging contract: outcome + latency + recipient_ref + subject only. The
    body (which carries one-time links/tokens) is never logged at any level.
    """
    if not delivery_configured(cfg):
        logger.warning(
            "EMAIL not delivered (no SMTP configured) outcome=no_provider to_ref=%s subject=%r",
            recipient_ref(to), subject,
        )
        return False
    msg = EmailMessage()
    msg["From"] = cfg.SMTP_FROM or cfg.SMTP_USER or "no-reply@aruora.local"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    started = time.monotonic()
    try:
        with smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT, timeout=15) as s:
            if cfg.SMTP_USER:
                s.starttls()
                s.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
            s.send_message(msg)
        logger.info(
            "EMAIL accepted outcome=sent to_ref=%s subject=%r latency_ms=%d",
            recipient_ref(to), subject, int((time.monotonic() - started) * 1000),
        )
        return True
    except Exception as exc:  # noqa: BLE001 — never crash the request on mail failure
        # Exception str may contain provider detail but never our token/body.
        logger.warning(
            "EMAIL outcome=failed to_ref=%s subject=%r latency_ms=%d error=%s",
            recipient_ref(to), subject,
            int((time.monotonic() - started) * 1000), exc.__class__.__name__,
        )
        return False

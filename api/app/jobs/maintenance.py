"""WS08-08 — data lifecycle maintenance.

Periodic purge of EXPIRED security/operational state so the database does not
accumulate dead rows forever:

  - ``auth_session`` rows that are revoked/expired older than the session
    retention window (kept briefly for audit, then gone);
  - ``auth_one_time_token`` rows past their expiry + retention window
    (password reset / email verify — single-use by ``used_at``);
  - finished ``jobs`` past the WS07 retention window (``JOB_RETENTION_HOURS``);
  - raw ``analytics_events`` past the raw-retention window (aggregates derived
    before deletion stay authoritative for WML windows).

EXPLICITLY OUT OF SCOPE (never purged here): attempts, cards, programs,
milestones, lessons, mocks, feedback, the AI usage ledger, admin audit.
Learning history is user-owned data governed by the published retention
policy and account deletion — not by a maintenance cron.

Runs from the Celery beat schedule (worker-beat service) and can be triggered
manually via POST /api/internal/maintenance/run (MAINTENANCE_TOKEN-guarded).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete


def _utc_naive(dt: datetime) -> datetime:
    """Normalise to naive-UTC so SQLite (naive) and Postgres (aware) compare."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _purge_dead_sessions(repo, cutoff: datetime) -> int:
    """Delete sessions that can never authenticate again AND whose audit
    retention window has passed (revoked, or absolutely expired)."""
    from app.data.models import AuthSession

    cutoff_naive = _utc_naive(cutoff)
    with repo.session_factory() as s:
        n = s.execute(
            delete(AuthSession).where(
                AuthSession.revoked_at.isnot(None),
                AuthSession.revoked_at < cutoff_naive,
            )
        ).rowcount or 0
        # Sessions never revoked but absolutely expired are equally dead; they
        # had no revocation timestamp, so age them from absolute_expires_at.
        n += s.execute(
            delete(AuthSession).where(
                AuthSession.revoked_at.is_(None),
                AuthSession.absolute_expires_at < cutoff_naive,
            )
        ).rowcount or 0
        s.commit()
        return int(n)


def _purge_expired_tokens(repo, cutoff: datetime) -> int:
    """Delete one-time tokens (reset/verify) whose expiry is older than the
    retention window — they are cryptographically dead, kept only for audit."""
    from app.data.models import AuthOneTimeToken

    with repo.session_factory() as s:
        n = s.execute(
            delete(AuthOneTimeToken).where(
                AuthOneTimeToken.expires_at < _utc_naive(cutoff)
            )
        ).rowcount or 0
        s.commit()
        return int(n)


def run_maintenance(repo, cfg, now: datetime | None = None) -> dict:
    """Execute every purge and return per-target row counts (ops telemetry;
    contains no learner content)."""
    now = now or datetime.now(timezone.utc)
    return {
        "sessions": _purge_dead_sessions(
            repo, now - timedelta(hours=cfg.SESSION_RETENTION_HOURS)
        ),
        "one_time_tokens": _purge_expired_tokens(
            repo, now - timedelta(hours=cfg.OTT_RETENTION_HOURS)
        ),
        "jobs": repo.jobs_purge_expired(
            now - timedelta(hours=cfg.JOB_RETENTION_HOURS)
        ),
        "analytics_events": repo.purge_old_analytics_events(
            older_than=now - timedelta(days=cfg.ANALYTICS_RETENTION_DAYS)
        ),
    }

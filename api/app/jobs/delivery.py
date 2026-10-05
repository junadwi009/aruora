"""Transactional outbox, bounded publication recovery and atomic execution claims.

Publish is at-least-once. Execution uses a DB compare-and-set, never a
read-then-write check. Uncertain running work is NOT replayed automatically:
without provider idempotency that could charge the learner twice.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, or_, select, update
from app.data.models import Job, JobDispatch

log = logging.getLogger(__name__)
MAX_DELIVERIES = 100


def utcnow():
    return datetime.now(timezone.utc)


def claim_job(repo, job_id: str) -> bool:
    now = utcnow()
    with repo.session_factory() as s:
        result = s.execute(update(Job).execution_options(synchronize_session=False).where(
            Job.id == job_id, Job.status == "queued",
            or_(Job.expires_at.is_(None), Job.expires_at > now),
        ).values(status="running", started_at=now, attempts=Job.attempts + 1))
        claimed = result.rowcount == 1
        if claimed:
            s.execute(delete(JobDispatch).where(JobDispatch.job_id == job_id))
        s.commit()
        return claimed


def dispatch_one(repo, job_id: str, dispatch, *, now=None) -> bool:
    """Lease and publish an intent. Failure leaves it durable for the sweeper.

    Nothing in the error log includes broker URLs, credentials or payloads.
    Repeated delivery is safe even if publish succeeded before the connection
    broke: only claim_job can admit a handler.
    """
    now = now or utcnow()
    with repo.session_factory() as s:
        intent = s.get(JobDispatch, job_id)
        job = s.get(Job, job_id)
        if intent is None or job is None:
            return False
        if job.status != "queued":
            s.delete(intent)
            s.commit()
            return False
        expiry = job.expires_at
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if (expiry and expiry <= now) or intent.attempts >= MAX_DELIVERIES:
            s.execute(update(Job).execution_options(synchronize_session=False).where(Job.id == job_id, Job.status == "queued").values(
                status="expired" if expiry and expiry <= now else "failed",
                error_code="DISPATCH_EXHAUSTED", error_message="Job delivery expired; submit a new request.",
                completed_at=now, payload={}))
            s.delete(intent)
            s.commit()
            return False
        # This update arbitrates competing API/beat publishers. Delay also
        # covers an accepted message that is waiting behind earlier tasks.
        delay = min(300, 30 * (2 ** min(intent.attempts, 4)))
        lease = s.execute(update(JobDispatch).execution_options(synchronize_session=False).where(
            JobDispatch.job_id == job_id, JobDispatch.not_before <= now,
        ).values(not_before=now + timedelta(seconds=delay), attempts=JobDispatch.attempts + 1))
        queue = job.queue
        leased = lease.rowcount == 1
        s.commit()
    if not leased:
        return False
    try:
        dispatch(job_id, queue, {})
        return True
    except Exception:
        log.warning("job_publish_deferred jobId=%s", job_id)
        return False


def recover_pending(repo, dispatch, *, now=None, limit=100) -> int:
    now = now or utcnow()
    with repo.session_factory() as s:
        ids = list(s.scalars(select(JobDispatch.job_id).where(
            JobDispatch.not_before <= now).order_by(JobDispatch.not_before).limit(limit)))
    return sum(dispatch_one(repo, jid, dispatch, now=now) for jid in ids)


def fail_uncertain_running(repo, *, now=None, older_than_sec=900) -> int:
    """A hard-crashed job may have reached the provider. Never blindly replay."""
    now = now or utcnow()
    with repo.session_factory() as s:
        n = s.execute(update(Job).execution_options(synchronize_session=False).where(
            Job.status == "running", Job.started_at < now - timedelta(seconds=older_than_sec),
        ).values(status="failed", error_code="JOB_OUTCOME_UNCERTAIN",
                 error_message="Processing was interrupted. Check saved progress before submitting new work.",
                 completed_at=now, payload={})).rowcount
        s.commit()
        return n

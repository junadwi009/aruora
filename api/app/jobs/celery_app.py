"""Celery worker, beat and publisher share one explicit broker contract.

The CLI imports `celery` directly. Publishers use make_celery(redis_url).
Neither path may accidentally fall back to an unconfigured AMQP broker.
Job results remain in PostgreSQL; only job IDs cross the Redis broker.
"""
from __future__ import annotations

import os
from celery import Celery
from kombu import Queue

QUEUE_CONCURRENCY_HINTS = {
    "asr": 1,
    "llm_score": 2,
    "llm_generate": 1,
    "mail": 2,
}


def _settings() -> dict:
    """Return independent configuration objects without a broker override."""
    return {
        "result_backend": None,
        "task_queues": [Queue(name) for name in QUEUE_CONCURRENCY_HINTS],
        "task_routes": {"app.jobs.run_job": {"queue": "llm_generate"}},
        "task_default_queue": "llm_generate",
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "worker_prefetch_multiplier": 1,
        "task_track_started": True,
        "task_serializer": "json",
        "accept_content": ["json"],
        "broker_connection_retry_on_startup": True,
        "broker_connection_timeout": 5,
        "task_publish_retry_policy": {
            "max_retries": 2, "interval_start": 0,
            "interval_step": 0.5, "interval_max": 1,
        },
        "beat_schedule": {
            "ws08-data-lifecycle-maintenance": {
                "task": "app.jobs.run_maintenance",
                "schedule": float(os.getenv("MAINTENANCE_INTERVAL_S", "3600")),
            },
        },
    }


def _environment_broker() -> str:
    url = os.getenv("REDIS_URL", "").strip()
    if not url and os.getenv("APP_ENV", "development") == "production":
        raise RuntimeError("Production Celery requires REDIS_URL")
    # The in-memory broker is explicitly local/test-only, never an implicit
    # attempt to contact an AMQP service that this stack does not provide.
    return url or "memory://"


celery = Celery("aruora_jobs", broker=_environment_broker())
celery.conf.update(_settings())
_celery_by_url: dict[str, Celery] = {}


def make_celery(redis_url: str) -> Celery:
    """Publisher configuration must preserve the caller's broker URL."""
    url = (redis_url or "").strip()
    if not url:
        raise ValueError("A broker URL is required for queued dispatch")
    app = _celery_by_url.get(url)
    if app is None:
        app = Celery("aruora_jobs", broker=url)
        app.conf.update(_settings())
        _celery_by_url[url] = app
    return app


@celery.task(name="app.jobs.run_job", bind=True, max_retries=0, acks_late=True)
def run_job(self, job_id: str) -> None:  # pragma: no cover - worker process
    from app.jobs.handlers import execute_job
    execute_job(job_id, _worker_context())


@celery.task(name="app.jobs.run_maintenance", ignore_result=True)
def run_maintenance() -> None:  # pragma: no cover - worker process
    from app.jobs.maintenance import run_maintenance as _sweep
    ctx = _worker_context()
    _sweep(ctx["repo"], ctx["cfg"])


def _worker_context() -> dict:  # pragma: no cover - worker process
    from app.config import Config
    from app.data.db import init_engine
    from app.data.repositories import Repository
    from app.services.llm import LlmGateway
    from sqlalchemy.orm import sessionmaker

    cfg = Config({})
    engine = init_engine(cfg.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return {"repo": Repository(Session), "cfg": cfg,
            "gateway": LlmGateway(cfg)}


def requeue_stale_jobs(repo, older_than_sec: int = 900) -> int:
    """Mark stale running rows queued. Delivery recovery remains a separate
    operation; this function alone does not republish a broker message."""
    from app.data.models import Job
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_sec)
    with repo.session_factory() as s:
        rows = s.query(Job).filter(
            Job.status == "running", Job.started_at.isnot(None),
        ).all()
        n = 0
        for j in rows:
            started = j.started_at
            if started is None:
                continue
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if started < cutoff:
                j.status = "queued"
                n += 1
        s.commit()
        return n

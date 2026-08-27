"""WS07-04 — Celery + Redis queue split and worker bootstrap.

Queues (separate worker processes in production — heavy queues never share
all slots with critical security mail):

  - ``llm_generate``  shared Task Pool replenishment (background, budgeted)
  - ``llm_score``     calibrated scoring (when scoring moves to async)
  - ``asr``           speech transcription (low concurrency, WS06 adopts)
  - ``mail``          security/transactional mail

Workers bootstrap their own DB context from the environment (the same
``DATABASE_URL``/config contract as the API). ``task_acks_late`` +
``worker_prefetch_multiplier=1`` mean a crashed worker re-delivers the job;
``execute_job`` is idempotent under redelivery (only ``queued`` rows run) and
``requeue_stale_jobs`` recovers rows stuck ``running`` after a hard crash.

Run locally (with REDIS_URL set):
    celery -A app.jobs.celery_app:celery worker -Q llm_generate,llm_score -c 2
    celery -A app.jobs.celery_app:celery worker -Q asr,mail -c 1
"""
from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab  # noqa: F401  (future periodic jobs)
from kombu import Queue

QUEUE_CONCURRENCY_HINTS = {
    # documentation for the deployment topology (docker-compose worker
    # services): keep ASR slots scarce; scoring/generation separate from mail
    "asr": 1,
    "llm_score": 2,
    "llm_generate": 1,
    "mail": 2,
}

celery = Celery("aruora_jobs")
celery.conf.update(
    broker_url="",            # set in make_celery(cfg.REDIS_URL)
    result_backend=None,      # job state lives in our DB, not the broker
    task_queues=[
        Queue("asr"),
        Queue("llm_score"),
        Queue("llm_generate"),
        Queue("mail"),
    ],
    task_routes={"app.jobs.run_job": {"queue": "llm_generate"}},
    task_default_queue="llm_generate",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
)

_celery_by_url: dict[str, Celery] = {}


def make_celery(redis_url: str) -> Celery:
    """One Celery app per broker URL (cached — send_task is cheap after this)."""
    app = _celery_by_url.get(redis_url)
    if app is None:
        app = Celery("aruora_jobs", broker=redis_url)
        app.conf.update(celery.conf)
        _celery_by_url[redis_url] = app
    return app


@celery.task(name="app.jobs.run_job", bind=True, max_retries=0, acks_late=True)
def run_job(self, job_id: str) -> None:  # pragma: no cover - worker process
    """Worker-side task: execute one job with bounded retries (WS07-06)."""
    from app.jobs.handlers import execute_job
    execute_job(job_id, _worker_context())


# WS08-08: periodic data-lifecycle maintenance — purges ONLY dead security
# state (expired sessions/tokens) and retained operational rows (finished
# jobs, raw analytics). Learning history is never touched here.
celery.conf.beat_schedule = {
    "ws08-data-lifecycle-maintenance": {
        "task": "app.jobs.run_maintenance",
        "schedule": float(os.getenv("MAINTENANCE_INTERVAL_S", "3600")),
    },
}


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
    """Crash recovery (worker boot / periodic): jobs stuck ``running`` (worker
    died mid-flight) go back to ``queued``; the Celery dispatcher layer re-
    delivers them. Returns the number of requeued jobs."""
    from app.data.models import Job
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_sec)
    with repo.session_factory() as s:
        rows = s.query(Job).filter(
            Job.status == "running",
            Job.started_at.isnot(None),
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

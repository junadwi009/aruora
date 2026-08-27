"""JobService — job records, idempotency, backpressure (WS07-03/05/07).

A job is a persistent DB row (unguessable UUID id, user-scoped status lookup,
safe error surface) plus a dispatch into a queue. Two dispatch modes:

  - ``queued``  (REDIS_URL set): dispatched to Celery on the job's queue;
                backpressure checked against the broker queue depth.
  - ``inline``  (no Redis — offline dev / self-host): the dispatcher runs the
                handler synchronously in-request; backpressure is a no-op.

Idempotency (WS07-05): a client-supplied (or system-generated) key binds a
job to (user, job type, canonical payload hash). A duplicate submission with
the SAME payload returns the existing job — the provider is called at most
once. The same key with a DIFFERENT payload is rejected (409), so a reused
key can never silently trigger unrelated work. Keys are bounded by the job
retention window (``JOB_RETENTION_HOURS``).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from app.errors import ApiError

QUEUES = ("asr", "llm_score", "llm_generate", "mail")


def canonical_payload_hash(payload: dict) -> str:
    """Stable hash of the canonical request — order-insensitive, no raw PII
    leaves the process (the hash is stored, not the rendering)."""
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _dispatch_inline(job_id: str, queue: str, payload: dict, ctx) -> None:
    """Synchronous dispatcher: execute now (offline dev / test path)."""
    from app.jobs.handlers import execute_job
    execute_job(job_id, ctx)


class JobService:
    def __init__(self, repo, cfg, gateway=None, dispatcher=None,
                 redis_client=None) -> None:
        self._repo = repo
        self._cfg = cfg
        self._gateway = gateway
        self._redis = redis_client
        # Deployment topology: queued iff REDIS_URL is configured. The
        # dispatcher is the execution mechanism and may be overridden (the
        # "eager" sentinel / a callable) for tests and offline tooling.
        self.mode = "queued" if cfg.REDIS_URL else "inline"
        if dispatcher == "eager":
            self._dispatch = self._inline_dispatch
        elif dispatcher is not None:
            self._dispatch = dispatcher
            if not cfg.REDIS_URL:
                self.mode = "inline"
        elif cfg.REDIS_URL:
            self._dispatch = self._celery_dispatch
        else:
            self._dispatch = self._inline_dispatch

    # ── context handed to handlers ────────────────────────────────────────
    def _ctx(self) -> dict:
        return {"repo": self._repo, "cfg": self._cfg, "gateway": self._gateway}

    def _inline_dispatch(self, job_id, queue, payload) -> None:
        _dispatch_inline(job_id, queue, payload, self._ctx())

    def _celery_dispatch(self, job_id, queue, payload) -> None:
        from app.jobs.celery_app import make_celery
        make_celery(self._cfg.REDIS_URL).send_task(
            "app.jobs.run_job", args=[job_id], queue=queue
        )

    # ── backpressure (WS07-07) ─────────────────────────────────────────────
    def queue_depth(self, queue: str) -> int:
        if self._redis is None:
            return 0
        try:
            return int(self._redis.llen(queue))
        except Exception:
            # Cannot observe the broker → assume the worst, protect the wallet.
            return int(self._cfg.QUEUE_MAX_DEPTH)

    def _check_backpressure(self, queue: str) -> None:
        if self._redis is None:
            return
        depth = self.queue_depth(queue)
        if depth >= int(self._cfg.QUEUE_MAX_DEPTH):
            raise ApiError(
                "BACKPRESSURE",
                "The practice queue is full right now — please try again in a few minutes",
                503,
                details=[{"retryAfter": 30}],
            )

    # ── enqueue (WS07-03/05) ───────────────────────────────────────────────
    def enqueue(
        self,
        job_type: str,
        *,
        queue: str,
        payload: dict,
        user_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[dict, bool]:
        """Create (and dispatch) a job. Returns (job, created).

        With ``idempotency_key``: same user+type+key+payload → existing job,
        ``created=False``; same key with a different payload → 409.
        """
        payload = dict(payload or {})
        payload_hash = canonical_payload_hash(payload)
        # The stored key embeds the owner so ONE unique index binds both user
        # jobs and system jobs (NULL user_id rows are distinct in SQL unique
        # indexes — a composite index would silently dedupe nothing).
        scoped_key = None
        if idempotency_key:
            owner = f"u:{user_id}" if user_id is not None else "sys"
            scoped_key = f"{job_type}:{owner}:{str(idempotency_key)[:90]}"

        if scoped_key:
            existing = self._repo.job_by_idempotency(user_id, scoped_key)
            if existing is not None:
                if existing["payloadHash"] != payload_hash:
                    raise ApiError(
                        "IDEMPOTENCY_CONFLICT",
                        "This idempotency key was already used with a different payload",
                        409,
                    )
                return existing, False

        self._check_backpressure(queue)

        job_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=int(self._cfg.JOB_RETENTION_HOURS)
        )
        try:
            job = self._repo.job_create(
                job_id,
                job_type,
                queue,
                payload,
                payload_hash,
                user_id=user_id,
                idempotency_key=scoped_key,
                expires_at=expires_at,
            )
        except Exception as e:
            # Concurrent enqueue racing the same idempotency key: the UNIQUE
            # (user_id, idempotency_key) index arbitrates — return the winner.
            # Any other DB failure is a real error.
            if scoped_key and not isinstance(e, ApiError):
                existing = self._repo.job_by_idempotency(user_id, scoped_key)
                if existing is not None:
                    if existing["payloadHash"] != payload_hash:
                        raise ApiError(
                            "IDEMPOTENCY_CONFLICT",
                            "This idempotency key was already used with a different payload",
                            409,
                        )
                    return existing, False
            raise

        self._dispatch(job_id, queue, payload)
        return job, True

    # ── user-scoped status lookup (WS07-03) ────────────────────────────────
    def get_status(self, job_id: str, user_id: int) -> dict | None:
        """Owner-only status view. Another user's job — or any system job —
        does not exist here (404 upstream). Expired jobs report ``expired``
        and never expose results (bounded retention, WS07-05)."""
        job = self._repo.job_get(job_id, user_id)
        if job is None:
            return None
        out = {k: v for k, v in job.items() if k not in ("payload", "payloadHash")}
        expires = job.get("expiresAt")
        if expires:
            try:
                exp = datetime.fromisoformat(expires)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > exp and out.get("status") in (
                    "succeeded", "failed", "cancelled",
                ):
                    out["status"] = "expired"
                    out.pop("result", None)
            except ValueError:
                pass
        return out

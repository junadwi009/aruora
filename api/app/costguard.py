"""WS07-02/08 — Cost controls: concurrency, provider budget, kill-switch, ledger.

Concept separation (WS07-02 — this module owns the non-rate-limit half):
  - **concurrency limit**: active heavy AI operations per authenticated user;
  - **daily/monthly quota**: product entitlement (see app.routes._gencap +
    ``GenUsage`` for the legacy inline-mode generation cap);
  - **provider budget**: global spend ceiling / alarm on the append-only
    AI usage ledger, with a hard emergency kill-switch.

The kill-switch and budget checks read only deployment config + the local DB
(``system_flags`` / ``ai_usage_ledger``), so they keep working when Redis is
down and are identical on every API worker. ``AI_BUDGET_KILL=1`` (env) is the
emergency switch: it fails closed and cannot be cleared from the app.

The ledger (WS07-08) is the single append-only accounting source of truth;
``GenUsage.count`` remains temporarily for inline-mode compatibility only and
must never become the billing source of truth. Pool serves are never recorded
as billable generation events (WS07-10 cost precedence).
"""
from __future__ import annotations

import threading
import time

from app.errors import ApiError
from app.session import current_uid

AI_HALTED_FLAG = "ai_budget_halt"


# ── Kill-switch / provider budget ─────────────────────────────────────────────

def ai_halt_reason(cfg, repo) -> str | None:
    """Return why paid AI is halted, or None when AI may proceed.

    Precedence: emergency env switch → admin flag → daily budget ceiling.
    """
    if getattr(cfg, "AI_BUDGET_KILL", False):
        return "kill_switch"
    try:
        if (repo.flag_get(AI_HALTED_FLAG) or "").strip().lower() in ("1", "true", "halt"):
            return "admin_halt"
    except Exception:
        # Cannot verify the switch → fail closed (never spend unverified).
        return "unverified"
    cap = int(getattr(cfg, "AI_DAILY_BUDGET_MICROS", 0) or 0)
    if cap > 0:
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if repo.ledger_sum_cost(start, now + timedelta(seconds=1)) >= cap:
            return "budget_exceeded"
    return None


def ensure_ai_available(cfg, repo) -> None:
    """Raise a retryable 503 when paid inference must not start. Account,
    history, export and deletion endpoints never call this — a budget halt
    must not take core account functionality down (WS07 required test)."""
    reason = ai_halt_reason(cfg, repo)
    if reason is None:
        return
    friendly = {
        "kill_switch": "AI features are temporarily paused for maintenance",
        "admin_halt": "AI features are temporarily paused — please try again later",
        "unverified": "AI features are temporarily unavailable — please try again",
        "budget_exceeded": "Daily AI budget reached — practice resumes tomorrow",
    }[reason]
    raise ApiError("AI_BUDGET_HALTED", friendly, 503)


# ── Concurrency limit (WS07-02) ───────────────────────────────────────────────

class ConcurrencyLimiter:
    """Bounds ACTIVE heavy operations per key (user+op).

    Redis backend: INCR + EXPIRE(NX) with a crash-safe TTL, DECR on release —
    shared across all workers. In-process fallback for offline self-host (the
    gunicorn worker count already bounds total concurrency there).
    """

    def __init__(self, redis_client=None) -> None:
        self._r = redis_client
        self._local: dict[str, tuple[int, int]] = {}
        self._lock = threading.Lock()

    def acquire(self, key: str, limit: int, ttl_sec: int) -> bool:
        limit = max(1, limit)
        if self._r is not None:
            full = f"cnc:{key}"
            pipe = self._r.pipeline()
            pipe.incr(full)
            pipe.expire(full, max(1, ttl_sec), nx=True)
            count = int(pipe.execute()[0])
            if count > limit:
                # Denied attempts must not leave the slot counter elevated.
                self._r.decr(full)
                return False
            return True
        now = int(time.monotonic() * 1000)
        with self._lock:
            count, expires = self._local.get(key, (0, 0))
            if expires <= now:
                count = 0
            if count >= limit:
                return False
            self._local[key] = (count + 1, now + ttl_sec * 1000)
            return True

    def release(self, key: str) -> None:
        if self._r is not None:
            full = f"cnc:{key}"
            try:
                n = int(self._r.decr(full))
                if n < 0:
                    # Floor guard: stale/corrupted counters reset, never stick.
                    pipe = self._r.pipeline()
                    pipe.set(full, 0)
                    pipe.expire(full, 60)
                    pipe.execute()
            except Exception:
                pass
            return
        with self._lock:
            count, expires = self._local.get(key, (0, 0))
            self._local[key] = (max(0, count - 1), expires)

    def slot(self, key: str, limit: int, ttl_sec: int):
        return _ConcurrencySlot(self, key, limit, ttl_sec)


class _ConcurrencySlot:
    def __init__(self, limiter, key, limit, ttl_sec) -> None:
        self._l, self._k, self._limit, self._ttl = limiter, key, limit, ttl_sec

    def __enter__(self):
        if not self._l.acquire(self._k, self._limit, self._ttl):
            raise ApiError(
                "CONCURRENCY_LIMIT",
                "You already have an evaluation in progress — please wait for it to finish",
                429,
            )
        return self

    def __exit__(self, *exc):
        self._l.release(self._k)
        return False


# ── Ledger recording (WS07-08) ────────────────────────────────────────────────

def record_llm_usage(
    repo,
    *,
    cost_center: str,
    op: str,
    meta: dict | None,
    user_id: int | None = None,
    skill: str | None = None,
    band: str | None = None,
    status: str = "ok",
    error_code: str | None = None,
    job_id: str | None = None,
) -> None:
    """Append one ledger row from gateway ``_meta_llm`` audit metadata.

    Never raises into the learning flow: analytics/cost failure must not roll
    back a successfully completed learning action (AGENTS analytics rule).
    """
    try:
        m = meta or {}
        cost_usd = m.get("costUsd")
        cost_micros = None
        cost_source = None
        if cost_usd is not None:
            try:
                cost_micros = int(round(float(cost_usd) * 1_000_000))
                cost_source = "provider_reported"
            except (TypeError, ValueError):
                cost_micros, cost_source = None, None
        repo.ledger_add(
            cost_center=cost_center,
            op=op,
            user_id=user_id,
            skill=skill,
            band=band,
            provider=m.get("provider"),
            model_requested=m.get("requestedModel"),
            model_used=m.get("resolvedModel") or m.get("requestedModel"),
            input_tokens=m.get("promptTokens"),
            output_tokens=m.get("completionTokens"),
            reasoning_tokens=m.get("reasoningTokens"),
            cached_tokens=m.get("cachedTokens"),
            cost_micros=cost_micros,
            cost_source=cost_source,
            status=status,
            error_code=error_code,
            cache_hit=bool(m.get("cachedTokens")),
            job_id=job_id,
        )
    except Exception:
        pass


def ai_concurrency_key(op: str, uid: int | None = None) -> str:
    uid = uid if uid is not None else current_uid()
    return f"{op}:u:{uid if uid is not None else 'anon'}"

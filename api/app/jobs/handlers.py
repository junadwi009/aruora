"""Job handlers + retry policy (WS07-06/07-10).

Retry policy per job type (WS07-06):
  - retry ONLY classified transient errors (provider 429/5xx/network → the
    gateway surfaces those as ``LLM_UNAVAILABLE``);
  - bounded attempts with exponential backoff + jitter;
  - NO retry on invalid model output (``LLM_BAD_OUTPUT``) — repairing bad
    output needs an explicit repair policy, not silent respend;
  - no infinite provider fallback loops.

Shared-content replenishment (WS07-10): ``replenish_pool`` is a SYSTEM cost
centre. It never consumes a learner's ``GenUsage`` entitlement — pool serves
are not billable generation events. One idempotent job exists per pool bucket
per daily generation epoch, so concurrent learner requests cannot spawn a
synchronous generation storm; a depleted pool enqueues replenishment instead.
"""
from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, timezone

from app.errors import ApiError
from app.routes._gencap import public_result, check_band

# cost centre + operation recorded per job type (ledger rows, WS07-08)
JOB_COST_CENTERS = {
    "replenish_pool": "pool_replenish",
    "score_writing": "learner_scoring",
    "score_speaking": "learner_scoring",
    "generate_custom": "learner_generation",
    "aura_chat": "aura",
    "transcribe": "asr",
}

JOB_OPS = {
    "replenish_pool": "generate",
    "score_writing": "score",
    "score_speaking": "score",
    "generate_custom": "generate",
    "aura_chat": "aura",
    "transcribe": "asr",
}

# Retryable = transient infrastructure/provider trouble. Invalid output,
# validation failures, budget halts and bugs are NEVER retried.
_RETRY_POLICY = {
    "replenish_pool": {"retry_codes": {"LLM_UNAVAILABLE"}, "max_attempts": 3},
}
_DEFAULT_POLICY = {"retry_codes": set(), "max_attempts": 1}

_BACKOFF_BASE_S = 2.0
_BACKOFF_CAP_S = 30.0


def _policy(job_type: str) -> dict:
    return _RETRY_POLICY.get(job_type, _DEFAULT_POLICY)


def is_retryable(job_type: str, error_code: str, attempts: int) -> bool:
    p = _policy(job_type)
    return (
        error_code in p["retry_codes"]
        and attempts < p["max_attempts"]
    )


def _backoff_sleep(attempt: int) -> None:
    delay = min(_BACKOFF_CAP_S, _BACKOFF_BASE_S * (2 ** max(0, attempt - 1)))
    time.sleep(delay * (0.5 + random.random() / 2))


def safe_job_error(e: Exception) -> tuple[str, str]:
    """Map any failure to a SAFE (code, message) pair. Raw provider errors,
    stack traces and key material never reach the job record or the API."""
    if isinstance(e, ApiError):
        return e.code, e.message
    return "INTERNAL_JOB_ERROR", "The job failed — please try again shortly"


def replenish_pool(payload: dict, ctx: dict) -> tuple[dict, dict | None]:
    """Grow one pool bucket (skill, band) by one VALIDATED set (WS27 §13).

    System cost centre: NO GenUsage increment. Pipeline:
      generate → schema/answer-key validation → exact-duplicate check →
      activate (or quarantine with quality flags).

    Accounting (27 §29): rejected generations (schema/quality/duplicate) ARE
    counted in the ledger as status='rejected' so content economics are not
    understated. Budget-aware: when the daily replenishment envelope is
    exhausted the job is cancelled (not failed) — budget pressure stops
    low-priority replenishment first (WS07-10 cost precedence), never
    silently downgrades calibrated scoring.
    """
    repo, cfg, gateway = ctx["repo"], ctx["cfg"], ctx["gateway"]
    skill = str(payload.get("skill", ""))
    band = check_band(payload.get("band"))

    if repo.count_sets(skill, band) >= cfg.POOL_TARGET:
        return {"status": "already_full", "skill": skill, "band": band}, None

    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if repo.ledger_count_ops(day_start, now + timedelta(seconds=1),
                             "pool_replenish") >= max(0, cfg.REPLENISH_DAILY_BUDGET):
        raise ApiError("REPLENISH_BUDGET_EXHAUSTED",
                       "Daily replenishment budget reached", 429)

    from app.costguard import record_llm_usage
    from app.services import task_pool

    out = gateway.generate("generate", skill=skill, band=band)
    meta = out.pop("_meta_llm", None)
    cleaned = public_result(out)
    cost_center_kwargs = dict(skill=skill, band=band, meta=meta)

    def _ledger(status: str, error_code: str | None = None) -> None:
        record_llm_usage(repo, cost_center="pool_replenish", op="generate",
                         status=status, error_code=error_code,
                         **cost_center_kwargs)

    # 1. Deterministic validation (schema + answer-key consistency).
    ok, flags = task_pool.validate_candidate(skill, band, cleaned)
    if not ok:
        # Quarantine with flags: audit trail without ever serving the item.
        repo.add_task_bank_set(
            skill, band, dict(cleaned), source="generated",
            status="quarantined", quality_flags={"flags": flags[:20]},
            generation_meta=_gen_meta(meta), pool_kind="practice_adaptive",
        )
        _ledger("rejected", "LLM_BAD_OUTPUT")
        return {"status": "rejected", "skill": skill, "band": band,
                "flags": flags[:5]}, meta

    # 2. Exact-duplicate rejection (canonical content hash, 27 §14).
    chash = task_pool.content_hash(cleaned)
    if repo.find_set_by_hash(skill, band, chash):
        _ledger("rejected", "DUPLICATE")
        return {"status": "rejected", "skill": skill, "band": band,
                "reason": "duplicate"}, meta

    # 3. Activate.
    new_id = repo.add_task_bank_set(
        skill, band, dict(cleaned), source="generated", status="active",
        content_hash=chash, generation_meta=_gen_meta(meta),
        gen_cost_micros=_cost_micros(meta), pool_kind="practice_adaptive",
    )
    if new_id is None:
        # Concurrent duplicate slipped past the probe — same economics.
        _ledger("rejected", "DUPLICATE")
        return {"status": "rejected", "skill": skill, "band": band,
                "reason": "duplicate"}, meta

    _ledger("ok")
    return {"status": "generated", "skill": skill, "band": band}, meta


def _gen_meta(meta: dict | None) -> dict:
    """Generation provenance stored with the task (never learner-exposed)."""
    m = meta or {}
    return {
        "provider": m.get("provider"),
        "modelRequested": m.get("requestedModel"),
        "modelUsed": m.get("resolvedModel") or m.get("requestedModel"),
    }


def _cost_micros(meta: dict | None) -> int | None:
    cost_usd = (meta or {}).get("costUsd")
    if cost_usd is None:
        return None
    try:
        return int(round(float(cost_usd) * 1_000_000))
    except (TypeError, ValueError):
        return None


HANDLERS = {
    "replenish_pool": replenish_pool,
}


def execute_job(job_id: str, ctx: dict, sleep=_backoff_sleep) -> None:
    """Run one job to a terminal state: bounded retries for classified
    transient errors, safe error surfacing, ledger row for failed AI work.

    Idempotent under redelivery: a job already ``running``/terminal is left
    alone (crash recovery requeues stale ``running`` rows separately).
    """
    repo = ctx["repo"]
    job = repo.job_get(job_id)
    if job is None or job["status"] != "queued":
        return
    job_type = job["type"]
    handler = HANDLERS.get(job_type)
    if handler is None:
        repo.job_fail(job_id, "UNKNOWN_JOB_TYPE", "No handler for this job type")
        return

    repo.job_set_running(job_id)
    attempts = int(job.get("attempts") or 0) + 1
    while True:
        try:
            result, meta = handler(job["payload"], ctx)
            m = meta or {}
            repo.job_set_succeeded(
                job_id,
                result,
                provider=m.get("provider"),
                model_requested=m.get("requestedModel"),
                model_used=m.get("resolvedModel") or m.get("requestedModel"),
            )
            return
        except ApiError as e:
            if is_retryable(job_type, e.code, attempts):
                attempts += 1
                sleep(attempts - 1)
                continue
            code, message = safe_job_error(e)
            if code == "REPLENISH_BUDGET_EXHAUSTED":
                # Expected budget-pressure outcome, not a malfunction:
                # replenishment stops before calibrated scoring is touched.
                repo.job_cancel(job_id, code, message)
            else:
                repo.job_fail(job_id, code, message)
                _record_failed(repo, ctx, job, code)
            return
        except Exception:
            repo.job_fail(job_id, "INTERNAL_JOB_ERROR",
                          "The job failed — please try again shortly")
            _record_failed(repo, ctx, job, "INTERNAL_JOB_ERROR")
            return


def _record_failed(repo, ctx, job, code: str) -> None:
    """Ledger row for a failed AI operation (never fabricates a result)."""
    center = JOB_COST_CENTERS.get(job["type"])
    if center is None:
        return
    try:
        payload = job.get("payload") or {}
        repo.ledger_add(
            cost_center=center,
            op=JOB_OPS.get(job["type"], "unknown"),
            skill=payload.get("skill"),
            band=payload.get("band"),
            status="failed",
            error_code=code,
            job_id=job["id"],
        )
    except Exception:
        pass

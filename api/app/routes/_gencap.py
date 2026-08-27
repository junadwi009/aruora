"""Shared token-efficiency helpers for generation routes.

WS05 additions:
- band values are validated against a closed allow-list (422 otherwise);
- gateway responses pass through :func:`public_result`, which strips
  underscore-prefixed audit keys (``_meta_llm``) before anything is stored in
  the task pool or returned to learners — internal metadata never becomes
  pool content.
"""
import re
from datetime import datetime, timezone

from app.errors import ApiError
from app.routes._analytics import emit

GEN_CAP_CODE = "GEN_CAP_REACHED"

# Closed set of supported CEFR-ish level tags across seed + generated pools.
_BAND_RE = re.compile(r"^(A1A2|A2|B1|B2|C1|C2)$")


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def cap_reached(uid: int, repo, cfg) -> bool:
    if cfg.DAILY_GEN_CAP <= 0:
        return False
    return repo.gen_count_today(uid, today_utc()) >= cfg.DAILY_GEN_CAP


def note_generation(uid: int, repo) -> None:
    repo.gen_incr_today(uid, today_utc())


def check_band(value) -> str:
    """Validate an untrusted band request value against the allowed set."""
    band = str(value or "").strip()
    if not _BAND_RE.match(band):
        raise ApiError("VALIDATION", "Unsupported band/level", 422)
    return band


def public_result(payload: dict) -> dict:
    """Strip internal (underscore-prefixed) keys from an LLM result."""
    if isinstance(payload, dict):
        return {k: v for k, v in payload.items() if not str(k).startswith("_")}
    return payload


def serve_or_generate(skill: str, default_band: str, uid: int, repo, cfg, gateway, body, jobs=None) -> dict:
    """
    Pool-freeze + daily-cap policy shared by reading & listening.

    Inline mode (default, no REDIS_URL — self-host behaviour preserved):
    - Pool full (count_sets >= POOL_TARGET) → serve a random stored set, no LLM.
    - Under target but daily cap reached → serve from pool if any, else 429.
    - Otherwise → generate, grow the pool, count the generation, return it.
    A new band starts with an empty pool, so generation resumes on level-up.

    Queued mode (REDIS_URL set — WS27 §25 transition policy):
    - pool-first, generate-second: the learner ALWAYS receives an eligible
      pooled task selected with per-user anti-repeat exposure (27 §9);
    - the request path is inference-free — pool underfill ENQUEUES a system
      replenishment job (idempotent per bucket per daily epoch, background
      budget envelope) instead of generating synchronously;
    - a learner entitlement is NEVER decremented for pool content, and an
      unservable bucket answers 503 POOL_EMPTY (retryable).
    """
    band = check_band((body or {}).get("band", default_band))

    # WS21 — content-free task-served analytics (WS27 economics input).
    def _served(source: str, payload: dict, *, served_band: str = band,
                repeat: bool = False, context: str = "practice") -> dict:
        emit("practice_task_served", skill=skill, source=source,
             difficulty_bucket=served_band, repeat_within_cooldown=repeat,
             selection_context=context)
        return payload

    if jobs is not None and getattr(jobs, "mode", "inline") == "queued":
        from app.services import task_pool

        served = task_pool.serve_next(skill, band, uid, repo, cfg)
        underfilled = repo.count_active_sets(skill, band) < cfg.POOL_TARGET
        if served is not None:
            if underfilled:
                try:  # best-effort background replenishment (27 §12)
                    jobs.enqueue(
                        "replenish_pool",
                        queue="llm_generate",
                        payload={"skill": skill, "band": band},
                        idempotency_key=f"{skill}:{band}:{today_utc()}",
                    )
                except ApiError:
                    pass  # duplicate race / backpressure — serving still works
            out = served["payload"]
            return _served(
                "pool", public_result(out) if isinstance(out, dict) else out,
                served_band=served["servedFrom"]["band"],
                repeat=served["repeat"], context=served["context"],
            )
        try:
            jobs.enqueue(
                "replenish_pool",
                queue="llm_generate",
                payload={"skill": skill, "band": band},
                idempotency_key=f"{skill}:{band}:{today_utc()}",
            )
        except ApiError:
            pass  # duplicate race / backpressure — the learner answer is below
        raise ApiError(
            "POOL_EMPTY",
            "New practice content is being prepared — please try again shortly",
            503,
            details=[{"retryAfter": 30}],
        )

    if repo.count_sets(skill, band) >= cfg.POOL_TARGET:
        return _served("pool", public_result(repo.serve_set(skill, band)) or {})

    if cap_reached(uid, repo, cfg):
        served = repo.serve_set(skill, band) or repo.serve_any_set(skill)
        if served is not None:
            return _served("pool", public_result(served))
        raise ApiError(GEN_CAP_CODE, "Daily generation limit reached", 429)

    out = gateway.generate("generate", skill=skill, band=band)
    cleaned = public_result(out)
    repo.add_set(skill, band, dict(cleaned))
    note_generation(uid, repo)
    return _served("custom_generation", cleaned)

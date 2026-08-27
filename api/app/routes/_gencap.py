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

    Inline mode (default, no REDIS_URL — behaviour preserved):
    - Pool full (count_sets >= POOL_TARGET) → serve a random stored set, no LLM.
    - Under target but daily cap reached → serve from pool if any, else 429.
    - Otherwise → generate, grow the pool, count the generation, return it.
    A new band starts with an empty pool, so generation resumes on level-up.

    Queued mode (jobs configured with REDIS_URL — WS07-10 migration rule):
    - pool serves stay free and inference-free;
    - pool underfill ENQUEUES a system replenishment job (idempotent per
      bucket per daily epoch, background budget envelope) instead of doing a
      synchronous learner-triggered generation;
    - a learner entitlement is NEVER decremented for pool content, and an
      empty pool answers 503 POOL_EMPTY (retryable) instead of generating
      inline under concurrent traffic.
    """
    band = check_band((body or {}).get("band", default_band))

    # WS21 — content-free task-served analytics (WS27 economics input).
    def _served(source: str, payload: dict) -> dict:
        # repeat_within_cooldown becomes real once WS27 per-user exposure lands.
        emit("practice_task_served", skill=skill, source=source,
             difficulty_bucket=band, repeat_within_cooldown=False)
        return payload

    if repo.count_sets(skill, band) >= cfg.POOL_TARGET:
        return _served("pool", public_result(repo.serve_set(skill, band)) or {})

    if jobs is not None and getattr(jobs, "mode", "inline") == "queued":
        served = repo.serve_set(skill, band) or repo.serve_any_set(skill)
        if served is not None:
            return _served("pool", public_result(served))
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

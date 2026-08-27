"""WS27 — AI usage policy service: entitlements + derived usage counters.

Two separated layers (27 §7):

* **Product entitlement** — what a learner may DO (custom generations,
  scored submissions). Understandable limits, never raw token counts. The
  legacy ``GenUsage(user, day, count)`` table remains the temporary
  compatibility projection backing the custom-generation entitlement; it is
  NOT the financial source of truth and will be retired once every route
  consumes this policy service (27 §26 Stage E).
* **Internal cost accounting** — derived, read-only aggregates over the
  append-only ``ai_usage_ledger`` (the billing source of truth, WS07-08).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.errors import ApiError

GEN_CAP_CODE = "GEN_CAP_REACHED"


def _today_window(day: str | None = None) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if day:
        start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


# ── product entitlement: learner-owned custom generation ─────────────────────

def custom_generation_allowed(uid: int, repo, cfg, day: str | None = None) -> bool:
    """True when the learner may spend a fresh-generation entitlement today.

    Pool serves NEVER call this — only explicitly learner-owned generations
    (topic vocabulary, personalized lesson plans, pronunciation targets).
    """
    if cfg.DAILY_GEN_CAP <= 0:
        return False
    start, end = _today_window(day)
    return repo.gen_count_today(uid, start.strftime("%Y-%m-%d")) < cfg.DAILY_GEN_CAP


def require_custom_generation(uid: int, repo, cfg) -> None:
    """Raise the stable 429 product error when the entitlement is exhausted."""
    if not custom_generation_allowed(uid, repo, cfg):
        raise ApiError(GEN_CAP_CODE, "Daily generation limit reached", 429)


def note_custom_generation(uid: int, repo) -> None:
    """Consume one custom-generation entitlement (compatibility projection)."""
    repo.gen_incr_today(uid, datetime.now(timezone.utc).strftime("%Y-%m-%d"))


# ── derived usage counters (read-only projections of the ledger) ─────────────

def usage_summary(repo, day: str | None = None) -> dict:
    """Fast rollup for dashboards (27 §6.5/§21). Derived from the append-only
    ledger — never the source of truth itself."""
    start, end = _today_window(day)
    from app.costguard import ai_halt_reason

    return {
        "day": start.strftime("%Y-%m-%d"),
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "ops": {
            "pool_serves": 0,  # pool serves are ledger-free by design (cost 0)
            "pool_replenish": repo.ledger_count_ops(start, end, "pool_replenish"),
            "learner_scoring": repo.ledger_count_ops(start, end, "learner_scoring"),
            "learner_generation": repo.ledger_count_ops(start, end, "learner_generation"),
            "aura": repo.ledger_count_ops(start, end, "aura"),
            "asr": repo.ledger_count_ops(start, end, "asr"),
        },
        "costMicros": repo.ledger_sum_cost(start, end),
    }

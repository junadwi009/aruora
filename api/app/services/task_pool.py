"""WS27 — Task Pool service: selection, exposure, validation, dedup.

Pool-first economics (27 §2): a learner asking for practice receives an
eligible pooled task; only learner-specific work (scoring, explicit custom
generation) pays for inference.

Selection (27 §9) — eligible-filter + preference order, not naive random:
  eligible  = status ``active`` AND matching bucket (skill+band);
  preferred = never served to this user → outside the repeat cooldown →
              least-recently-served (documented degraded repeat);
  fallback  = another active bucket of the SAME skill only (never cross
              skill; the actually-served difficulty is recorded and returned).

Lifecycle (27 §13): candidates enter the bank only after schema validation
(WS05 contracts) and deterministic answer-key consistency checks; failures
are quarantined with quality flags (audit trail, never served). Exact
duplicates are rejected via canonical content hash (27 §14, layer 1) —
post-generation rejection, never growing prompt context.

No raw learner content and no generation/admin metadata ever travel in
exposure rows or served responses.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone

from app.errors import ApiError

VALID_SKILLS = ("reading", "listening")


def content_hash(payload) -> str:
    """Canonical normalized content hash for exact-duplicate rejection."""
    try:
        canon = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"))
    except (TypeError, ValueError):
        return ""
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


# ── lifecycle: validation before activation (27 §13) ─────────────────────────

def validate_candidate(skill: str, band: str, payload: dict) -> tuple[bool, list[str]]:
    """Deterministic pre-activation gate. Returns (ok, quality_flags).

    Layer 1 — the WS05 output contract for the skill (schema shape, field
    bounds, control-char stripping). Layer 2 — answer-key consistency checks
    deterministic code can enforce without an LLM validator.
    """
    flags: list[str] = []
    try:
        from app.services.llm_output import validate_llm_output
        validate_llm_output(skill, payload)
    except ApiError as e:
        flags.append(f"schema:{e.message[:120]}")
        return False, flags

    questions = payload.get("questions") or []
    for i, q in enumerate(questions):
        options = q.get("options")
        answer = (q.get("answer") or "").strip()
        if options and answer and answer not in options:
            flags.append(f"answer_key:q{i}:answer-not-in-options")
    if flags:
        return False, flags
    return True, []


# ── selection (27 §9) ─────────────────────────────────────────────────────────

def _pick(rows, exposures, cooldown_cutoff, now) -> tuple[int, dict, bool] | None:
    """rows: [(id, payload, serve_count)]; exposures: {id: last_served_at}.

    Preference: unseen → cooldown-ready (random among ready) → least recent.
    """
    unseen = [r for r in rows if r[0] not in exposures]
    if unseen:
        chosen = random.choice(unseen)
        return chosen[0], chosen[1], False
    ready = [
        r for r in rows
        if r[0] in exposures and (exposures[r[0]] or _epoch()) < cooldown_cutoff
    ]
    if ready:
        chosen = random.choice(ready)
        return chosen[0], chosen[1], True
    if rows:
        least = min(rows, key=lambda r: exposures.get(r[0]) or _epoch())
        return least[0], least[1], True
    return None


def _epoch():
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def serve_next(skill: str, default_band: str, user_id: int, repo, cfg,
               band: str | None = None) -> dict | None:
    """Select + serve ONE eligible pooled task for the user.

    Returns None when no valid task exists (caller decides fallback/replenish).
    The response carries NO internal metadata and NO inventory ids — content
    IDs that reveal pool size/order are never exposed to learners (27 §23).
    """
    band = band or default_band
    rows = repo.list_active_sets(skill, band)
    if not rows:
        return None

    now = datetime.now(timezone.utc)
    cooldown = timedelta(hours=max(0, int(getattr(cfg, "POOL_REPEAT_COOLDOWN_HOURS", 24))))
    cutoff = _naive(now - cooldown)
    exposures = repo.recent_exposure_map(user_id)

    pick = _pick(rows, exposures, cutoff, now)
    context = "practice"
    if pick is None:
        # Documented adjacent-bucket fallback: same skill, different difficulty.
        # Never crosses skill (exam-variant integrity, 27 §25).
        alt_rows = repo.list_active_sets(skill, None)
        pick = _pick(alt_rows, exposures, cutoff, now)
        context = "fallback_adjacent"
    if pick is None:
        return None

    set_id, payload, _serve_count = pick
    served_band = band
    if context == "fallback_adjacent":
        served_band = repo.band_of_set(set_id) or band
    repeat = set_id in exposures
    repo.record_exposure(user_id, set_id, context, repeat)
    repo.increment_serve_count(set_id)
    return {
        "payload": payload,
        "servedFrom": {"skill": skill, "band": served_band},
        "repeat": repeat,
        "context": context,
        "servedAt": now.isoformat(),
    }

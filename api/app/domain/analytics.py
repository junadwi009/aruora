"""
WS21 — Product analytics domain: taxonomy, envelope integrity, WML.

Design rules (docs/production-readiness/21):

- SERVER-AUTHORITATIVE: completion events are emitted by the API after the
  learning action has actually succeeded — never by client declaration.
- CONTENT-FREE: properties are coarse, bounded, and allow-listed per event.
  Essays, transcripts, audio, answer keys, prompts, emails, phones, tokens and
  secrets must never land here. Enforcement lives in ``build_envelope``.
- COHORT-AWARE: cohort_id / acquisition_source are server-owned and validated
  against a closed allow-list; arbitrary client segmentation strings are
  rejected. Lecturer-controlled and voluntary cohorts stay separable.
- WML (North Star): Weekly Meaningful Learners — distinct learners with at
  least one qualifying learning action in a rolling 7-day window. Openings,
  views, messages, and streak-only actions never qualify.
- FAIL-OPEN: analytics is a best-effort layer (see routes/_analytics.py);
  an analytics failure must never roll back a completed learning action.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone

# ── Versioned taxonomy ────────────────────────────────────────────────────────

EVENT_VERSION = 1

# Event families that exist as surfaces TODAY. Future gated events (pod_*,
# whatsapp_*, tutor_*) are deliberately absent until those surfaces ship.
ALL_EVENTS = {
    # funnel (client beacon allowed for *_view / *_started only)
    "landing_view",
    "signup_started",
    "signup_completed",
    "onboarding_started",
    "goal_selected",
    "destination_selected",
    "target_band_selected",
    "deadline_added",
    "onboarding_completed",
    "placement_started",
    "placement_skill_started",
    "placement_skill_completed",
    "placement_abandoned",
    "placement_completed",
    "result_viewed",
    "program_viewed",
    "program_selected",
    "practice_started",
    "practice_task_served",
    "practice_completed",
    "writing_submitted",
    "speaking_submitted",
    "mock_completed",
    "feedback_viewed",
    "feedback_helpful",
    "app_returned",
    # study pool opt-in surfaces (interest/opt-in only, no community features)
    "peer_interest_viewed",
    "peer_opt_in",
    "whatsapp_opt_in",
    "human_help_interest",
}

# Events a signed-in/anonymous CLIENT may declare. Everything else in
# ALL_EVENTS is server-emitted after a verified action.
CLIENT_EMITTABLE = {
    "landing_view",
    "signup_started",
    "onboarding_started",
    "app_returned",
    "result_viewed",
    "program_viewed",
    "practice_started",
    "feedback_viewed",
    "peer_interest_viewed",
}

# ── WML qualifying actions (North Star definition) ───────────────────────────

WML_QUALIFYING_EVENTS = {
    "practice_completed",
    "writing_submitted",
    "speaking_submitted",
    "mock_completed",
}

WML_WINDOW_DAYS = 7

# ── Acquisition / cohort dimensions (server-owned) ───────────────────────────

ACQUISITION_SOURCES = {
    "lecturer_partner",
    "linkedin_founder",
    "referral",
    "campus_community",
    "organic",
    "paid",
    "other",
}

_COHORT_RE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")

# Cohort naming contract for UAT waves (21 §cohort pattern). Lecturer cohorts
# MUST keep the lecturer_uat_ prefix so they are never merged silently into
# voluntary-cohort funnels.
LECTURER_COHORT_PREFIX = "lecturer_uat_"


def validate_cohort_id(value: str | None) -> str | None:
    """Server-side validation for cohort identifiers."""
    if not value:
        return None
    v = value.strip().lower()
    if not _COHORT_RE.match(v) or len(v) > 40:
        raise ValueError("invalid cohort_id")
    return v


def validate_acquisition_source(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lower()
    if v not in ACQUISITION_SOURCES:
        raise ValueError("invalid acquisition_source")
    return v


# ── Property integrity ────────────────────────────────────────────────────────

# Keys that may never appear in analytics properties under any name. Values
# are also scanned for email/phone shapes as defence-in-depth.
_FORBIDDEN_KEY_RE = re.compile(
    r"(essay|transcript|audio|answer|prompt|body|email|phone|whatsapp|"
    r"password|secret|token|api_key|authorization)",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{7,}$")

MAX_PROPERTIES = 12
MAX_STR_LEN = 120
MAX_LIST_LEN = 8


def _clean_value(value, depth: int = 0):
    """Coerce a property value to a bounded, content-free scalar."""
    if depth > 2:
        raise ValueError("property nesting too deep")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        v = float(value)
        if v != v or v in (float("inf"), float("-inf")):  # NaN / inf
            raise ValueError("numeric property must be finite")
        return v
    if isinstance(value, str):
        s = value.strip()
        if not s:
            raise ValueError("empty string property")
        if len(s) > MAX_STR_LEN:
            raise ValueError("string property too long")
        if _EMAIL_RE.match(s) or _PHONE_RE.match(s):
            raise ValueError("PII-shaped value rejected")
        return s
    if isinstance(value, list):
        if len(value) > MAX_LIST_LEN:
            raise ValueError("list property too long")
        return [_clean_value(v, depth + 1) for v in value]
    raise ValueError("unsupported property type")


def clean_properties(properties: Mapping | None) -> dict:
    """Validate + normalise a properties mapping (fail-closed)."""
    if properties is None:
        return {}
    if not isinstance(properties, Mapping):
        raise ValueError("properties must be an object")
    if len(properties) > MAX_PROPERTIES:
        raise ValueError("too many properties")
    cleaned: dict = {}
    for key, value in properties.items():
        k = str(key)
        if not re.match(r"^[a-z][a-z0-9_]{0,39}$", k):
            raise ValueError(f"invalid property key {k!r}")
        if _FORBIDDEN_KEY_RE.search(k):
            raise ValueError(f"forbidden property key {k!r}")
        cleaned[k] = _clean_value(value)
    return cleaned


# ── Envelope ─────────────────────────────────────────────────────────────────

def build_envelope(
    event_name: str,
    *,
    user_id: int | None = None,
    anonymous_id: str | None = None,
    cohort_id: str | None = None,
    acquisition_source: str | None = None,
    occurred_at: datetime | None = None,
    properties: Mapping | None = None,
    event_id: str | None = None,
) -> dict:
    """Build a validated analytics envelope, or raise ValueError."""
    if event_name not in ALL_EVENTS:
        raise ValueError(f"unknown event {event_name!r}")
    if user_id is None and not anonymous_id:
        # Every event must be attributable at least to a pseudonymous session.
        raise ValueError("user_id or anonymous_id required")

    props = clean_properties(properties)
    # Server-owned dimensions: never accept raw client cohort strings.
    cohort_id = validate_cohort_id(cohort_id)
    acquisition_source = validate_acquisition_source(acquisition_source)

    return {
        "event_name": event_name,
        "event_version": EVENT_VERSION,
        "event_id": event_id or str(uuid.uuid4()),
        "occurred_at": (occurred_at or datetime.now(timezone.utc)).isoformat(),
        "user_id": user_id,
        "anonymous_id": anonymous_id,
        "cohort_id": cohort_id,
        "acquisition_source": acquisition_source,
        "properties": props,
    }


# ── WML computation (pure, reproducible) ────────────────────────────────────

def is_qualifying(name: str) -> bool:
    return name in WML_QUALIFYING_EVENTS


def weekly_meaningful_learners(
    rows: Iterable[tuple[int, str, datetime]],
    *,
    as_of: datetime,
    window_days: int = WML_WINDOW_DAYS,
) -> int:
    """
    Count distinct learners with ≥1 qualifying action inside the rolling
    window ending at ``as_of`` (inclusive).

    ``rows`` yields (user_id, event_name, occurred_at) triples — the raw
    material comes from the caller's scoped query, keeping this function pure
    and trivially reproducible in tests.
    """
    start = as_of - timedelta(days=window_days)
    end = as_of
    users: set[int] = set()
    for user_id, name, at in rows:
        if user_id is None or not is_qualifying(name):
            continue
        ts = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
        if start <= ts <= end:
            users.add(user_id)
    return len(users)


def qualifies_for_wml(name: str, occurred_at: datetime, *, as_of: datetime) -> bool:
    """Single-row convenience predicate for streaming/replay checks."""
    return weekly_meaningful_learners(
        [(1, name, occurred_at)], as_of=as_of
    ) == 1

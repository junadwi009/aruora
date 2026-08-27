"""WS21 — analytics emission helpers for routes.

FAIL-OPEN contract (21 §Analytics integrity / AGENTS.md): an analytics
failure must never roll back a successfully completed learning action. Every
emit is wrapped; the envelope is validated before persistence so a malformed
property set logs-and-drops instead of corrupting the store.

Server-authoritative events are emitted by the route AFTER the learning
action succeeds. Client beacons go through a strict allow-list
(CLIENT_EMITTABLE) so a hostile client cannot fabricate completion events —
completion metrics are computed from server-side truth only.
"""
from __future__ import annotations

import logging

from flask import current_app, request

from app.domain.analytics import (
    CLIENT_EMITTABLE,
    build_envelope,
    validate_acquisition_source,
    validate_cohort_id,
)

log = logging.getLogger("app.analytics")


def _session_uid():
    from app.session import current_uid
    return current_uid()


def emit(event_name: str, *, user_id: int | None = None, **properties) -> None:
    """Best-effort server-side emission. Never raises."""
    try:
        repo = current_app.config["REPO"]
        uid = user_id if user_id is not None else _session_uid()
        envelope = build_envelope(event_name, user_id=uid, properties=properties)
        repo.save_analytics_event(envelope)
    except Exception:  # noqa: BLE001 — analytics must be fail-open
        log.warning("analytics drop event=%s", event_name)


def emit_client_beacon(event_name: str, payload: dict, *,
                       anonymous_id: str | None = None) -> bool:
    """Validate + persist a CLIENT-declared event, restricted to the
    client-emittable allow-list. Returns True when accepted.

    Cohort/acquisition dimensions are taken from the SERVER-side profile (not
    the request body), keeping segmentation server-owned.
    """
    if event_name not in CLIENT_EMITTABLE:
        return False
    try:
        props = payload.get("properties") if isinstance(payload, dict) else None
        repo = current_app.config["REPO"]
        uid = _session_uid()
        cohort_id = source = None
        if uid is not None:
            from app.data.models import UserProfile
            with repo._sf() as s:  # narrow read; envelope validation still applies
                u = s.get(UserProfile, uid)
                if u is not None:
                    cohort_id = u.cohort_id
                    source = u.acquisition_source
        envelope = build_envelope(
            event_name,
            user_id=uid,
            anonymous_id=anonymous_id,
            cohort_id=cohort_id,
            acquisition_source=source,
            properties=props,
        )
        return repo.save_analytics_event(envelope)
    except Exception:  # noqa: BLE001
        log.warning("analytics beacon drop event=%s", event_name)
        return False


def capture_acquisition(user_id: int) -> None:
    """Attach acquisition/cohort from SERVER-trusted inputs at signup time.

    Accepts query params (?src=&cohort=) ONLY after validation against the
    closed allow-lists; anything invalid is silently dropped (organic). UAT
    cohort distribution (e.g. lecturer_uat_01 invite links) relies on this.
    """
    from app.domain.analytics import (
        validate_acquisition_source as _vas,
        validate_cohort_id as _vch,
    )
    try:
        src = _vas(request.args.get("src"))
        cohort = _vch(request.args.get("cohort"))
        if src or cohort:
            current_app.config["REPO"].set_acquisition(user_id, src, cohort)
    except Exception:  # noqa: BLE001 — never block signup on analytics
        log.warning("acquisition capture failed")


__all__ = ["emit", "emit_client_beacon", "capture_acquisition",
           "validate_acquisition_source", "validate_cohort_id"]

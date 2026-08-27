"""WS21 — analytics: taxonomy integrity, WML reproducibility, cohort separation,
and route-level server-authoritative emission."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.domain.analytics import (
    build_envelope,
    clean_properties,
    weekly_meaningful_learners,
    validate_acquisition_source,
    validate_cohort_id,
)
from app.errors import ApiError
from app.services.llm import LlmGateway


# ── Envelope / property integrity ─────────────────────────────────────────────

def test_unknown_event_rejected():
    with pytest.raises(ValueError, match="unknown event"):
        build_envelope("pod_joined", user_id=1)


def test_unattributable_event_rejected():
    with pytest.raises(ValueError, match="user_id or anonymous_id"):
        build_envelope("landing_view")


def test_arbitrary_cohort_string_rejected():
    with pytest.raises(ValueError, match="invalid cohort_id"):
        build_envelope("signup_completed", user_id=1, cohort_id="Best Coverts!!")


def test_arbitrary_acquisition_source_rejected():
    with pytest.raises(ValueError, match="invalid acquisition_source"):
        build_envelope("signup_completed", user_id=1, acquisition_source="tiktok")
    assert validate_acquisition_source("linkedin_founder") == "linkedin_founder"
    assert validate_cohort_id("lecturer_uat_01") == "lecturer_uat_01"


def test_pii_property_values_rejected():
    with pytest.raises(ValueError, match="PII-shaped"):
        clean_properties({"who": "learner@example.com"})
    with pytest.raises(ValueError, match="PII-shaped"):
        clean_properties({"contact": "+62 812 3456 7890"})


def test_forbidden_property_keys_rejected():
    for key in ("essay", "transcript", "audio", "answer_key", "api_key", "email"):
        with pytest.raises(ValueError, match="forbidden property key"):
            clean_properties({key: "x"})


def test_oversized_and_nested_properties_rejected():
    with pytest.raises(ValueError, match="too long"):
        clean_properties({"skill": "x" * 300})
    with pytest.raises(ValueError, match="too many properties"):
        clean_properties({f"p{i}": 1 for i in range(20)})
    with pytest.raises(ValueError, match="unsupported property type"):
        clean_properties({"deep": {"a": {"b": 1}}})


# ── WML math (North Star must be reproducible) ───────────────────────────────

NOW = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)


def _rows(*tuples):
    return list(tuples)


def test_wml_counts_distinct_users_once_per_week():
    rows = _rows(
        (1, "writing_submitted", NOW - timedelta(days=1)),
        (1, "writing_submitted", NOW - timedelta(days=2)),
        (2, "practice_completed", NOW - timedelta(days=3)),
        (2, "mock_completed", NOW - timedelta(days=4)),
    )
    assert weekly_meaningful_learners(rows, as_of=NOW) == 2


def test_wml_ignores_views_and_out_of_window_actions():
    rows = _rows(
        (3, "landing_view", NOW - timedelta(days=1)),          # view never counts
        (3, "app_returned", NOW - timedelta(days=1)),          # return never counts
        (4, "practice_completed", NOW - timedelta(days=8)),    # outside 7d window
        (5, "writing_submitted", NOW - timedelta(days=20)),    # far outside
    )
    assert weekly_meaningful_learners(rows, as_of=NOW) == 0


def test_wml_window_boundary_is_inclusive_and_rolling():
    at_edge = NOW - timedelta(days=7)
    rows = _rows((6, "speaking_submitted", at_edge))
    assert weekly_meaningful_learners(rows, as_of=NOW) == 1
    just_outside = NOW - timedelta(days=7, microseconds=1)
    rows = _rows((6, "speaking_submitted", just_outside))
    assert weekly_meaningful_learners(rows, as_of=NOW) == 0


# ── Repository layer ──────────────────────────────────────────────────────────

def _repo():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    repo = Repository(sessionmaker(bind=eng))
    # FKs are live (WS04): analytics rows need real owners.
    repo._uids = [
        repo.create_account("u1@example.com", "correct horse battery staple").id,
        repo.create_account("u2@example.com", "correct horse battery staple").id,
    ]
    return repo


def _env(user_id, name, when=NOW, cohort=None, source=None, props=None):
    return build_envelope(
        name, user_id=user_id, occurred_at=when,
        cohort_id=cohort, acquisition_source=source, properties=props,
    )


def test_save_event_is_idempotent_on_event_id():
    repo = _repo()
    env = _env(repo._uids[0], "mock_completed")
    assert repo.save_analytics_event(env) is True
    assert repo.save_analytics_event(env) is False     # retry deduped


def test_wml_query_counts_qualifying_only():
    repo = _repo()
    u1, u2 = repo._uids
    repo.save_analytics_event(_env(u1, "writing_submitted", when=NOW - timedelta(days=1)))
    repo.save_analytics_event(_env(u1, "landing_view", when=NOW - timedelta(days=1)))
    repo.save_analytics_event(_env(u2, "practice_completed", when=NOW - timedelta(days=9)))
    assert repo.weekly_meaningful_learners(as_of=NOW) == 1


def test_cohort_breakdown_keeps_lecturer_separate():
    repo = _repo()
    u1, u2 = repo._uids
    repo.save_analytics_event(_env(u1, "mock_completed", cohort="lecturer_uat_01",
                                   source="lecturer_partner"))
    repo.save_analytics_event(_env(u1, "mock_completed", cohort="lecturer_uat_01",
                                   source="lecturer_partner"))
    repo.save_analytics_event(_env(u2, "practice_completed", cohort="linkedin_uat_01",
                                   source="linkedin_founder"))
    rows = repo.analytics_by_cohort()
    by_cohort = {r["cohortId"]: r for r in rows}
    assert by_cohort["lecturer_uat_01"]["events"] == 2
    assert by_cohort["lecturer_uat_01"]["distinctUsers"] == 1
    assert by_cohort["linkedin_uat_01"]["distinctUsers"] == 1
    # never merged into one row
    assert len(rows) == 2


def test_purge_removes_only_old_rows():
    repo = _repo()
    repo.save_analytics_event(_env(repo._uids[0], "writing_submitted",
                                   when=NOW - timedelta(days=200)))
    repo.save_analytics_event(_env(repo._uids[1], "writing_submitted", when=NOW))
    n = repo.purge_old_analytics_events(older_than=NOW - timedelta(days=180))
    assert n == 1
    assert repo.analytics_counts()["writing_submitted"] == 1


def test_account_deletion_removes_user_events():
    """Analytics joins primary-data deletion governance (WS04/21)."""
    repo = _repo()
    u1, _ = repo._uids
    repo.save_analytics_event(_env(u1, "writing_submitted", when=NOW))
    repo.delete_account(u1)
    assert repo.analytics_counts().get("writing_submitted", 0) == 0


# ── Route emission (server-authoritative) ─────────────────────────────────────

def _client():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    repo = Repository(Session)
    app = create_app({"TESTING": True, "REPO": repo,
                      "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"}))})
    return app.test_client(), repo


def test_onboarding_emits_funnel_events():
    c, repo = _client()
    r = c.post("/api/onboarding", json={
        "name": "A", "goal": "work", "targetBand": 6.5, "examDate": "2027-03"})
    assert r.status_code == 200
    counts = repo.analytics_counts()
    assert counts.get("onboarding_completed") == 1
    assert counts.get("goal_selected") == 1
    assert counts.get("target_band_selected") == 1
    assert counts.get("deadline_added") == 1
    # coarse destination category only — no free text lands in analytics
    import json as _json
    with repo._sf() as s:
        from sqlalchemy import text
        raw = s.execute(text(
            "SELECT properties FROM analytics_events WHERE name = 'goal_selected'"
        )).scalar_one()
    props = raw if isinstance(raw, dict) else _json.loads(raw)
    assert props["goal"] == "work"


def test_writing_submission_emits_wml_event():
    c, repo = _client()
    c.post("/api/onboarding", json={"name": "A", "goal": "work", "targetBand": 6.5})
    r = c.post("/api/writing/evaluate", json={
        "taskType": "task2", "prompt": "p", "essay": "My essay text."})
    assert r.status_code == 200
    counts = repo.analytics_counts()
    assert counts.get("writing_submitted") == 1
    # No learner content may leak into analytics (only the task_type label).
    with repo._sf() as s:
        from sqlalchemy import text
        blob = s.execute(text(
            "SELECT group_concat(properties) FROM analytics_events"
        )).scalar_one()
    assert "My essay text." not in (blob or "")


def test_client_beacon_cannot_fabricate_completions():
    c, _ = _client()
    for event in ("writing_submitted", "practice_completed", "mock_completed",
                  "signup_completed", "totally_new_event"):
        r = c.post("/api/analytics/events", json={"event": event})
        assert r.status_code == 422


def test_client_beacon_accepts_allowed_view_event():
    c, repo = _client()
    r = c.post("/api/analytics/events", json={
        "event": "landing_view", "anonymousId": "anon-abc123"})
    assert r.status_code == 200
    assert repo.analytics_counts().get("landing_view") == 1


def test_admin_summary_gates_and_breaks_down_cohorts():
    c, repo = _client()
    # anonymous: 401/403, never data
    r = c.get("/api/admin/analytics/summary")
    assert r.status_code in (401, 403)

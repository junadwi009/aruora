"""WS20 — readiness contract engine + route (no percentages, fully explainable)."""

from datetime import datetime, timezone

from app.domain.readiness import (
    READINESS_METHOD_VERSION,
    build_readiness,
)

NOW = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)


def test_full_coverage_mean_and_priority():
    est = {"listening": 6.0, "reading": 6.5, "writing": 5.5, "speaking": 6.0}
    r = build_readiness(est, target_band=7.0, now=NOW)
    assert r["method"] == READINESS_METHOD_VERSION
    assert r["currentEstimate"] == 6.0          # mean 6.0, official rounding
    assert r["prioritySkill"] == "writing"       # largest gap (7.0-5.5=1.5)
    assert r["gap"] == 1.5
    assert r["evidenceCoverage"]["complete"] is True
    assert r["evidenceCoverage"]["assessed"] == 4


def test_partial_coverage_flags_missing_skills():
    r = build_readiness({"writing": 5.0}, target_band=6.5, now=NOW)
    assert r["currentEstimate"] == 5.0
    assert r["evidenceCoverage"] == {
        "assessed": 1, "total": 4, "complete": False,
        "missing": ["listening", "reading", "speaking"],
    }
    assert r["gap"] == 1.5


def test_no_evidence_never_fabricates_an_estimate():
    r = build_readiness({}, target_band=6.5, now=NOW)
    assert r["currentEstimate"] is None
    assert r["gap"] is None and r["prioritySkill"] is None
    assert "not an official" in r["disclaimer"]


def test_skill_targets_override_for_gap_ranking():
    est = {"listening": 6.0, "reading": 6.0, "writing": 6.0, "speaking": 6.0}
    r = build_readiness(est, target_band=6.5,
                        skill_targets={"writing": 7.5}, now=NOW)
    assert r["prioritySkill"] == "writing"       # 7.5-6.0 beats uniform 0.5 gaps
    assert r["skillTargets"]["writing"] == 7.5
    assert r["skillTargets"]["reading"] == 6.5


def test_no_percentage_field_exists():
    r = build_readiness({"writing": 6.0}, target_band=7.0, now=NOW)
    blob = str(r).lower()
    assert "percent" not in blob and "%" not in blob


def test_official_rounding_applies_to_estimate_mean():
    # mean = 6.25 -> rounds UP to 6.5 (WS02 official rules)
    est = {"listening": 6.0, "reading": 6.5, "writing": 6.0, "speaking": 6.5}
    r = build_readiness(est, target_band=7.0, now=NOW)
    assert r["currentEstimate"] == 6.5


# ── Route: GET /api/history/readiness ────────────────────────────────────────

def test_readiness_route_contract(client_with_seed):
    c = client_with_seed
    c.post("/api/onboarding", json={"name": "A", "goal": "work", "targetBand": 6.5})
    r = c.post("/api/writing/evaluate", json={
        "taskType": "task2", "prompt": "p", "essay": "Some practice essay text."})
    assert r.status_code == 200

    res = c.get("/api/history/readiness")
    assert res.status_code == 200
    body = res.get_json()
    assert body["method"] == "readiness-v0"
    assert body["targetBand"] == 6.5
    assert body["perSkill"]["writing"]["assessed"] is True
    assert body["perSkill"]["listening"]["assessed"] is False
    assert body["evidenceCoverage"]["complete"] is False
    assert body["prioritySkill"] == "writing"
    assert "%" not in str(body)


def test_readiness_route_requires_auth(client_with_seed):
    fresh = client_with_seed.application.test_client()
    r = fresh.get("/api/history/readiness")
    assert r.status_code == 401
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.services.llm import LlmGateway


def _client(overrides=None):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    repo = Repository(Session)
    gw = LlmGateway(Config({"LLM_MODE": "stub"}))
    cfg = {"TESTING": True, "REPO": repo, "GATEWAY": gw, "GATE_LOCK_SECONDS": 120}
    cfg.update(overrides or {})
    app = create_app(cfg)
    c = app.test_client()
    c.post("/api/account/register", json={"email": "u@example.com", "password": "correct horse battery staple"})
    return c

def _verify_current_user(c):
    me = c.get("/api/account/me").get_json()
    c.application.config["REPO"].set_email_verified(me["id"], True)

def test_status_starts_unlocked_and_not_locked():
    c = _client()
    r = c.get("/api/gate/status")
    assert r.status_code == 200
    j = r.get_json()
    assert j["locked"] is False and j["unlocked"] is False
    assert j["thresholdSeconds"] == 120


def test_heartbeat_accumulates_and_locks_at_threshold():
    c = _client()
    # heartbeat clamps to 2x interval; default interval 60 -> max 120/tick
    c.post("/api/gate/heartbeat", json={"seconds": 120})
    j = c.post("/api/gate/heartbeat", json={"seconds": 120}).get_json()
    assert j["activeSeconds"] == 240
    assert j["locked"] is True


def test_heartbeat_clamps_huge_jumps():
    """Integration resolution (WS09 x legacy gate clamp): two defensive layers.

    Layer 1 (WS09 edge): seconds > 7200 is rejected 422 BEFORE any LLM/DB work.
    Layer 2 (route clamp): in-range resumed-tab jumps (e.g. 5000) are clamped
    to 2x GATE_HEARTBEAT_SEC (60) -> +120s.
    """
    c = _client()
    r = c.post("/api/gate/heartbeat", json={"seconds": 99999})
    assert r.status_code == 422                       # edge rejects absurd input
    j = c.post("/api/gate/heartbeat", json={"seconds": 5000}).get_json()
    assert j["activeSeconds"] == 120                  # route clamps in-range jumps


def test_unlock_requires_valid_stars_and_insight():
    c = _client()
    assert c.post("/api/gate/unlock", json={"stars": 0, "insight": "x"}).status_code == 422
    assert c.post("/api/gate/unlock", json={"stars": 5, "insight": "short"}).status_code == 422
    ok = c.post("/api/gate/unlock", json={"stars": 4, "insight": "Great for listening practice, thanks!"})
    assert ok.status_code == 200 and ok.get_json()["unlocked"] is True


def test_unlock_makes_status_permanently_unlocked():
    c = _client()
    c.post("/api/gate/heartbeat", json={"seconds": 120})
    c.post("/api/gate/heartbeat", json={"seconds": 120})  # now locked
    c.post("/api/gate/unlock", json={"stars": 5, "insight": "Solid feedback on my essays here."})
    j = c.get("/api/gate/status").get_json()
    assert j["locked"] is False and j["unlocked"] is True


def test_admin_never_locked_and_can_list_feedback():
    c = _client(overrides={"ADMIN_EMAILS": "u@example.com"})

    _verify_current_user(c)

    c.post("/api/gate/heartbeat", json={"seconds": 120})
    c.post("/api/gate/heartbeat", json={"seconds": 120})

    assert c.get("/api/gate/status").get_json()["locked"] is False

    c.post(
        "/api/gate/unlock",
        json={
            "stars": 3,
            "insight": "Admin can read this insight row.",
        },
    )

    rows = c.get("/api/admin/feedback").get_json()
    assert any(r["stars"] == 3 for r in rows)


def test_unlock_is_idempotent_no_duplicate_feedback():
    c = _client(
        overrides={"ADMIN_EMAILS": "admin@example.com"}
    )

    r1 = c.post(
        "/api/gate/unlock",
        json={
            "stars": 4,
            "insight": "First unlock call with insight.",
        },
    )
    assert r1.status_code == 200
    assert r1.get_json()["unlocked"] is True

    r2 = c.post(
        "/api/gate/unlock",
        json={
            "stars": 2,
            "insight": "Second unlock call, should be a no-op.",
        },
    )
    assert r2.status_code == 200
    assert r2.get_json()["unlocked"] is True

    c.post("/api/account/logout")

    r = c.post(
        "/api/account/register",
        json={
            "email": "admin@example.com",
            "password": "correct horse battery staple",
        },
    )
    assert r.status_code == 200

    _verify_current_user(c)

    rows = c.get("/api/admin/feedback").get_json()

    assert len([r for r in rows if r["stars"] == 4]) == 1
    assert not any(r["stars"] == 2 for r in rows)


def test_gate_state_is_per_user():
    c = _client()
    c.post("/api/gate/heartbeat", json={"seconds": 120})
    c.post("/api/gate/heartbeat", json={"seconds": 120})
    j = c.get("/api/gate/status").get_json()
    assert j["activeSeconds"] == 240 and j["locked"] is True

    # switch to a second account on the same client
    c.post("/api/account/logout")
    c.post("/api/account/register", json={"email": "second@example.com", "password": "correct horse battery staple"})
    j2 = c.get("/api/gate/status").get_json()
    assert j2["activeSeconds"] == 0
    assert j2["locked"] is False

"""WS07-01/02/09 — rate limits: shared Redis windows, dimension keying,
abuse escalation, fail-closed behaviour, and route-level 429 metadata.

The WS07-01 required test — "two API processes share the same effective Redis
limit" — is modelled by two RateLimitService instances over ONE Redis client:
whichever instance counts the hit, both see the same window.
"""

import fakeredis
import pytest

from app import ratelimit
from app.ratelimit import (
    InProcessBackend,
    RateLimitService,
    RedisBackend,
    Rule,
    email_hash,
    rule_for,
)

IP = Rule(3, 60, "ip")
USER = Rule(3, 60, "user")
CRED = Rule(3, 60, "credential")


@pytest.fixture()
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)


# ── WS07-01: distribution + dimensions ───────────────────────────────────────

def test_two_api_processes_share_one_redis_limit(fake_redis):
    s1 = RateLimitService(RedisBackend(fake_redis), fail_closed=True)
    s2 = RateLimitService(RedisBackend(fake_redis), fail_closed=True)
    # Together the two "processes" get 3 hits in the window — not 3 each.
    assert s1.allow(IP, ip="1.1.1.1").allowed
    assert s2.allow(IP, ip="1.1.1.1").allowed
    assert s1.allow(IP, ip="1.1.1.1").allowed
    v = s2.allow(IP, ip="1.1.1.1")
    assert not v.allowed and v.retry_after >= 1


def test_user_quota_does_not_consume_other_users_quota(fake_redis):
    svc = RateLimitService(RedisBackend(fake_redis))
    for _ in range(3):
        assert svc.allow(USER, ip="9.9.9.9", user_id=1).allowed
    # User 1 is done; user 2 (same NAT IP) still has their own budget…
    assert svc.allow(USER, ip="9.9.9.9", user_id=2).allowed
    # …and an anonymous client on that IP is IP-keyed independently.
    assert svc.allow(USER, ip="9.9.9.9").allowed


def test_credential_abuse_bound_by_email_hash_across_ips(fake_redis):
    svc = RateLimitService(RedisBackend(fake_redis))
    # The same account attacked from three IPs: the email-hash counter binds.
    assert svc.allow(CRED, ip="1.1.1.1", email="victim@example.com").allowed
    assert svc.allow(CRED, ip="2.2.2.2", email="VICTIM@example.com ").allowed
    assert svc.allow(CRED, ip="3.3.3.3", email="victim@example.com").allowed
    assert not svc.allow(CRED, ip="4.4.4.4", email="victim@example.com").allowed
    # A different account from one of those IPs is unaffected (ip headroom).
    assert svc.allow(CRED, ip="3.3.3.3", email="other@example.com").allowed


def test_email_hash_normalization():
    assert email_hash("A@Example.com ") == email_hash("a@example.com")
    assert email_hash("a@example.com") != email_hash("b@example.com")
    assert email_hash("") is None and email_hash(None) is None


def test_rule_kinds():
    assert rule_for("/api/account/login").kind == "credential"
    assert rule_for("/api/writing/evaluate").kind == "user"
    assert rule_for("/api/health").kind == "ip"


# ── WS07-09: escalation ladder steps 1-2 ─────────────────────────────────────

@pytest.fixture()
def clock(monkeypatch):
    """Controllable wall for the in-process backend."""
    state = {"t": 10_000.0}
    monkeypatch.setattr(ratelimit, "time_ms", lambda: int(state["t"] * 1000))
    return state


def test_repeated_denials_tighten_the_bucket(clock):
    svc = RateLimitService(InProcessBackend(), escalate_after=1)
    rule = Rule(4, 60, "ip")
    for _ in range(4):
        assert svc.allow(rule, ip="p").allowed
    assert not svc.allow(rule, ip="p").allowed  # esc=1
    assert not svc.allow(rule, ip="p").allowed  # esc=2
    clock["t"] += 61  # window fully elapsed…
    assert svc.allow(rule, ip="p").allowed  # …but the bucket is tighter now
    assert not svc.allow(rule, ip="p").allowed  # effective limit is 4 >> 2 = 1


# ── fail-closed (WS07 exit criteria: security controls fail closed) ─────────

class _BrokenBackend(InProcessBackend):
    def check(self, *a, **k):
        raise ConnectionError("redis down")


def test_redis_outage_fails_closed_when_configured():
    svc = RateLimitService(_BrokenBackend(), fail_closed=True)
    v = svc.allow(IP, ip="1.1.1.1")
    assert not v.allowed and v.unavailable and v.retry_after >= 1


def test_redis_outage_fails_open_only_when_explicitly_configured():
    svc = RateLimitService(_BrokenBackend(), fail_closed=False)
    assert svc.allow(IP, ip="1.1.1.1").allowed


# ── route wiring: 429 + retry metadata, no internal architecture leaked ─────

@pytest.fixture()
def limiter_app(fake_redis):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app import create_app
    from app.config import Config
    from app.data.models import Base
    from app.data.repositories import Repository
    from app.kv import MemoryKV
    from app.services.llm import LlmGateway

    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    repo = Repository(sessionmaker(bind=eng))
    app = create_app({
        "TESTING": True,
        "REPO": repo,
        "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
        "KV": MemoryKV(),
        "RATE_LIMIT_ENABLED": "1",
        "RATE_LIMIT_TEST_FORCE": "1",
        "RATE_LIMIT_REDIS": fake_redis,
    })
    return app.test_client()


def test_route_level_429_carries_retry_metadata(limiter_app):
    c = limiter_app
    codes = [
        c.post("/api/account/login",
               json={"email": f"u{i}@example.com",
                     "password": "wrong-password-entirely"}).status_code
        for i in range(11)
    ]
    assert codes[-1] == 429
    # Either the WS07 limiter (Retry-After header) or the WS03 flow throttle
    # (details.retryAfter body field) tripped — both must expose retry info
    # without leaking internal quota architecture.
    resp = c.post("/api/account/login",
                  json={"email": "final@example.com",
                        "password": "wrong-password-entirely"})
    retry_ok = (
        resp.headers.get("Retry-After") is not None
        or "retryAfter" in (resp.get_json().get("error") or {}).get("details", {})
    )
    assert retry_ok
    body = resp.get_data(as_text=True)
    assert "redis" not in body.lower() and "queue" not in body.lower()

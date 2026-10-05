"""Regressions discovered by the full-image production smoke, not test bypasses."""
import fakeredis
import pytest
from app.ratelimit import InProcessBackend, RedisBackend, RateLimitService, rule_for


@pytest.fixture(params=["memory", "redis"])
def services(request):
    backend = InProcessBackend() if request.param == "memory" else RedisBackend(fakeredis.FakeRedis(decode_responses=True))
    return RateLimitService(backend), RateLimitService(backend)


def test_public_reads_do_not_consume_registration_and_login_limits(services):
    a, b = services
    for _ in range(40):
        assert a.allow(rule_for("/api/health/ready"), "shared-nat").allowed
    register = rule_for("/api/account/register")
    for i in range(register.limit):
        assert (a if i % 2 else b).allow(register, "shared-nat", email=f"synthetic-{i}@example.invalid").allowed
    assert not b.allow(register, "shared-nat", email="limit@example.invalid").allowed
    assert a.allow(rule_for("/api/account/login"), "shared-nat", email="learner@example.invalid").allowed


def test_registration_and_recovery_keep_separate_email_dimensions(services):
    a, b = services
    rule = rule_for("/api/account/register")
    for i in range(rule.limit):
        assert a.allow(rule, f"peer-{i}", email="same@example.invalid").allowed
    assert not b.allow(rule, "another-peer", email="SAME@example.invalid ").allowed
    assert b.allow(rule_for("/api/account/forgot"), "another-peer", email="same@example.invalid").allowed


def test_heavy_policies_do_not_consume_each_others_allowance(services):
    a, b = services
    writing = rule_for("/api/writing/evaluate")
    for _ in range(writing.limit):
        assert a.allow(writing, "peer", user_id=1).allowed
    assert not b.allow(writing, "peer", user_id=1).allowed
    assert b.allow(rule_for("/api/speaking/transcribe"), "peer", user_id=1).allowed
    assert b.allow(writing, "peer", user_id=2).allowed


def test_policy_keys_are_finite_not_raw_url_identifiers():
    assert rule_for("/api/jobs/one").bucket == rule_for("/api/jobs/two").bucket
    assert rule_for("/api/pronounce/first").bucket == rule_for("/api/pronounce/second").bucket
    assert rule_for("/api/account/login").bucket != rule_for("/api/account/reset").bucket


@pytest.mark.parametrize("operation", ["escalations", "check", "bump", "retry_after"])
def test_all_backend_failures_are_retryable_and_fail_closed(monkeypatch, operation):
    backend = InProcessBackend()
    def fail(*args, **kwargs):
        raise ConnectionError("Synthetic outage")
    if operation in ("bump", "retry_after"):
        monkeypatch.setattr(backend, "check", lambda *args: False)
    monkeypatch.setattr(backend, operation, fail)
    result = RateLimitService(backend).allow(rule_for("/api/account/login"), "peer")
    assert not result.allowed and result.unavailable and result.retry_after >= 1

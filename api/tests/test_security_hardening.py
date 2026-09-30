"""
Security-hardening regression tests (audit remediation).

Covers: SESSION_SECRET fail-closed guard, session-cookie flags, security
response headers, auth required on the paid-LLM endpoints, the NIST-style
password policy (WS03-04), SVG-avatar rejection, and the rate-limit
service unit (WS07-01/02 backend contract).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.ratelimit import InProcessBackend, RateLimitService, Rule, rule_for
from app.security.passwords import validate_new_password
from app.services.llm import LlmGateway


def _overrides(**extra):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    o = {
        "TESTING": True,
        "SESSION_SECRET": "test-secret",
        "REPO": Repository(Session),
        "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
    }
    o.update(extra)
    return o


def _client(**extra):
    return create_app(_overrides(**extra)).test_client()


# ── #1 CRITICAL: fail-closed on the default session secret ────────────────────

def test_default_session_secret_is_rejected_outside_testing():
    # TESTING is False and the secret is the built-in default → refuse to boot.
    with pytest.raises(RuntimeError):
        create_app({"TESTING": False, "SESSION_SECRET": "dev-secret-change-me"})


def test_real_secret_boots_fine():
    app = create_app(_overrides())
    assert app.secret_key == "test-secret"


# ── #4 cookie hardening + #12 security headers ───────────────────────────────

def test_session_cookie_flags():
    app = create_app(_overrides(COOKIE_SECURE=True, COOKIE_SAMESITE="Strict"))
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Strict"


def test_security_headers_present():
    r = _client().get("/api/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in r.headers


# ── #2 HIGH: paid-LLM endpoints require authentication ───────────────────────

@pytest.mark.parametrize("path,body", [
    ("/api/reading/generate", {"band": "B2"}),
    ("/api/listening/generate", {}),
    ("/api/vocab", {"topic": "travel"}),
    ("/api/pronounce/sentence", {"level": "B1"}),
    ("/api/pronounce/feedback", {"target": "x", "transcript": "x", "accuracy": 100, "missed": []}),
])
def test_llm_endpoints_require_auth(path, body):
    # No session established → 401 (previously these were fully open).
    r = _client().post(path, json=body)
    assert r.status_code == 401


def test_llm_endpoint_ok_when_signed_in():
    c = _client()
    c.post("/api/account/register", json={"email": "a@b.com", "password": "correct horse battery staple"})
    assert c.post("/api/reading/generate", json={"band": "B2"}).status_code == 200


# ── #10 password policy (WS03-04: NIST-style length + local blocklist) ───────

def test_short_password_rejected_on_register():
    r = _client().post("/api/account/register", json={"email": "x@y.com", "password": "short7!pass"})
    assert r.status_code == 422


def test_fifteen_char_password_accepted():
    r = _client().post("/api/account/register", json={"email": "x@y.com", "password": "eightchr-pass-15"})
    assert r.status_code == 200


def test_password_policy_unit():
    # spaces + unicode allowed, no composition rules
    assert validate_new_password("correct horse battery staple") == []
    assert validate_new_password("これはじゅうごもじのパスワード") == []
    # length floor
    assert any("15" in p for p in validate_new_password("short12chars!"))
    # upper bound
    assert any("128" in p for p in validate_new_password("x" * 129))
    # local common-password blocklist (privacy-preserving, no external call)
    assert validate_new_password("password123", min_chars=8) != []
    # context: never the email name
    assert any("email" in p for p in validate_new_password("arjuna-jogja-1234", context="arjuna@x.com"))


# ── #11 SVG avatar rejected ──────────────────────────────────────────────────

VALID_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
    "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

def test_svg_avatar_rejected():
    c = _client()
    c.post("/api/account/register", json={"email": "a@b.com", "password": "correct horse battery staple"})
    r = c.post("/api/account/avatar", json={"dataUrl": "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4="})
    assert r.status_code == 422
    ok = c.post("/api/account/avatar", json={"dataUrl": VALID_PNG})
    assert ok.status_code == 200


# ── #6 rate-limit service unit (WS07-01/02 backend contract) ─────────────────

_IP_RULE = Rule(3, 60, "ip")


def test_rate_limiter_blocks_after_limit():
    rl = InProcessBackend()
    got = [rl.check("k", 3, 60_000, f"m{i}") for i in range(4)]
    assert got == [True, True, True, False]


def test_rate_limit_service_denies_with_retry_after():
    svc = RateLimitService(InProcessBackend())
    verdicts = [svc.allow(_IP_RULE, ip="1.2.3.4") for _ in range(4)]
    assert [v.allowed for v in verdicts] == [True, True, True, False]
    assert verdicts[-1].retry_after >= 1


def test_rate_limit_service_credential_dimensions_must_both_allow():
    svc = RateLimitService(InProcessBackend())
    # Same IP, different accounts: the IP dimension is the shared budget.
    for i in range(3):
        assert svc.allow(_IP_RULE, ip="1.2.3.4", email=f"u{i}@x.com").allowed
    v = svc.allow(_IP_RULE, ip="1.2.3.4", email="other@x.com")
    assert not v.allowed


def test_rate_limit_rules_cover_credentials_and_llm():
    login = rule_for("/api/account/login")
    assert (login.limit, login.window_sec, login.kind) == (10, 60, "credential")
    writing = rule_for("/api/writing/evaluate")
    assert (writing.limit, writing.kind) == (20, "user")
    default = rule_for("/api/some/other")
    assert (default.limit, default.window_sec) == (300, 60)

"""
Security-hardening regression tests (audit remediation).

Covers: SESSION_SECRET fail-closed guard, session-cookie flags, security
response headers, auth required on the paid-LLM endpoints, the min-8 password
policy, SVG-avatar rejection, and the in-process rate limiter unit.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.ratelimit import RateLimiter, rule_for
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
    c.post("/api/account/register", json={"email": "a@b.com", "password": "secret123"})
    assert c.post("/api/reading/generate", json={"band": "B2"}).status_code == 200


# ── #10 password policy (min 8) ──────────────────────────────────────────────

def test_short_password_rejected_on_register():
    r = _client().post("/api/account/register", json={"email": "x@y.com", "password": "short7!"})
    assert r.status_code == 422


def test_eight_char_password_accepted():
    r = _client().post("/api/account/register", json={"email": "x@y.com", "password": "eightchr"})
    assert r.status_code == 200


# ── #11 SVG avatar rejected ──────────────────────────────────────────────────

def test_svg_avatar_rejected():
    c = _client()
    c.post("/api/account/register", json={"email": "a@b.com", "password": "secret123"})
    r = c.post("/api/account/avatar", json={"dataUrl": "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4="})
    assert r.status_code == 422
    ok = c.post("/api/account/avatar", json={"dataUrl": "data:image/png;base64,aGVsbG8="})
    assert ok.status_code == 200


# ── #6 rate limiter unit ─────────────────────────────────────────────────────

def test_rate_limiter_blocks_after_limit():
    rl = RateLimiter()
    t = 1000.0
    # 3 allowed within the window, 4th blocked.
    assert [rl.check("k", 3, 60, now=t + i * 0.1) for i in range(4)] == [True, True, True, False]


def test_rate_limiter_window_slides():
    rl = RateLimiter()
    assert rl.check("k", 1, 60, now=1000.0) is True
    assert rl.check("k", 1, 60, now=1030.0) is False   # still inside the 60s window
    assert rl.check("k", 1, 60, now=1061.0) is True    # window has passed


def test_rate_limit_rules_cover_credentials_and_llm():
    assert rule_for("/api/account/login") == (10, 60)
    assert rule_for("/api/writing/evaluate") == (20, 60)
    assert rule_for("/api/pronounce/sentence") == (30, 60)
    assert rule_for("/api/some/other") == (300, 60)     # global default

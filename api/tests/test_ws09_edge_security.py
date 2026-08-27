"""
WS09 — API/edge security tests.

Required checks from 09_API_EDGE_SECURITY.md:
- untrusted Host rejected (WS09-02);
- direct client cannot spoof the rate-limit IP through forwarded headers
  (WS09-03), and ProxyFix honors exactly one trusted proxy hop;
- cross-origin policy: CORS absent when not configured, exact origins (never
  wildcard-with-credentials) when it is (WS09-04);
- security-header snapshot + no-store caching on API responses (WS09-05);
- oversized / malformed bodies rejected with stable JSON before expensive work
  (WS09-03B/07);
- error responses contain no stack traces or secrets and carry a correlation
  id (WS09-08);
- health surfaces are split liveness / readiness / admin detail and leak no
  topology (WS09-10).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.services.llm import LlmGateway

PW = "correct horse battery staple"


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


# ── WS09-02: trusted hosts ────────────────────────────────────────────────────

def test_untrusted_host_rejected():
    c = _client(TRUSTED_HOSTS="aruora.app")
    r = c.get("/api/health", headers={"Host": "evil.example"})
    assert r.status_code == 421
    assert r.get_json()["error"]["code"] == "UNTRUSTED_HOST"


def test_trusted_host_accepted_with_port():
    c = _client(TRUSTED_HOSTS="aruora.app,www.aruora.app")
    ok = c.get("/api/health", headers={"Host": "aruora.app:8443"})
    assert ok.status_code == 200
    assert c.get("/api/health", headers={"Host": "www.aruora.app"}).status_code == 200


def test_unrestricted_when_trusted_hosts_unset():
    # offline/self-host dev default: any Host is accepted
    assert _client().get("/api/health", headers={"Host": "anything"}).status_code == 200


def test_tls_production_requires_trusted_hosts_at_boot():
    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        create_app({
            "TESTING": False,
            "SESSION_SECRET": "real-secret",
            "COOKIE_SECURE": True,
            "TRUSTED_HOSTS": "",
        })


# ── WS09-03: rate-limit IP cannot be spoofed via forwarded headers ───────────

def _bad_logins(c, n, headers_for):
    codes = []
    for i in range(n):
        codes.append(c.post(
            "/api/account/login",
            json={"email": f"u{i}@spam.example", "password": "totally-wrong-pw"},
            headers=headers_for(i),
        ).status_code)
    return codes


def test_forwarded_headers_cannot_rotate_rate_limit_key():
    # TRUSTED_PROXIES=0: no proxy in front → forwarded headers are NEVER
    # trusted. Rotating X-Real-IP/X-Forwarded-For must NOT rotate the limiter
    # bucket: the 11th attempt from the same socket peer is rate limited.
    c = _client(RATE_LIMIT_TEST_FORCE=True)
    codes = _bad_logins(
        c, 11,
        lambda i: {"X-Real-IP": f"10.0.0.{i}", "X-Forwarded-For": f"10.0.0.{i}"},
    )
    assert all(code == 401 for code in codes[:10])
    assert codes[-1] == 429  # same real peer — the headers were ignored


def test_proxyfix_uses_exactly_one_trusted_hop():
    # TRUSTED_PROXIES=1 (nginx → gunicorn): only the LAST XFF entry (the one
    # the trusted proxy appends) is the client IP; client-supplied earlier
    # entries are ignored and cannot be rotated.
    c = _client(RATE_LIMIT_TEST_FORCE=True, TRUSTED_PROXIES=1)
    chain = "203.0.113.7, 198.51.100.9"  # attacker-injected, proxy-appended
    codes = _bad_logins(c, 11, lambda i: {"X-Forwarded-For": chain})
    assert all(code == 401 for code in codes[:10])
    assert codes[-1] == 429  # same proxy-observed client 198.51.100.9

    # A genuinely different proxy-observed client is NOT blocked by that bucket.
    r = c.post(
        "/api/account/login",
        json={"email": "fresh@spam.example", "password": "totally-wrong-pw"},
        headers={"X-Forwarded-For": "198.51.100.1, 203.0.113.99"},
    )
    assert r.status_code == 401


# ── WS09-04: same-origin CORS policy ─────────────────────────────────────────

def _preflight(c, origin):
    return c.options(
        "/api/account/login",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )


def test_cors_absent_when_not_configured():
    c = _client(CORS_ORIGIN="")
    r = _preflight(c, "http://localhost:5173")
    assert "Access-Control-Allow-Origin" not in r.headers


def test_cors_exact_origin_when_configured():
    c = _client(CORS_ORIGIN="http://good.example")
    r = _preflight(c, "http://good.example")
    assert r.headers.get("Access-Control-Allow-Origin") == "http://good.example"
    assert r.headers.get("Access-Control-Allow-Credentials") == "true"
    # a different origin gets nothing
    assert "Access-Control-Allow-Origin" not in _preflight(c, "http://evil.example").headers


def test_cors_never_wildcards_with_credentials():
    c = _client(CORS_ORIGIN="http://good.example,http://other.example")
    for origin in ("http://good.example", "http://other.example"):
        assert _preflight(c, origin).headers["Access-Control-Allow-Origin"] == origin
    # the configured origin list is exact — no wildcard entry exists
    assert set(c.app.config["APP_CONFIG"].CORS_ORIGINS) == {
        "http://good.example", "http://other.example"}


# ── WS09-05: security-header snapshot on API responses ───────────────────────

def test_api_response_header_snapshot():
    r = _client().get("/api/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"
    assert "frame-ancestors 'none'" in r.headers.get("Content-Security-Policy", "")
    assert r.headers.get("Cache-Control") == "no-store"


# ── WS09-07/03B: request limits + contracts reject before expensive work ─────

def test_malformed_json_returns_stable_json_400():
    c = _client()
    r = c.post("/api/account/login", data="{not-json", content_type="application/json")
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "INVALID_JSON"
    assert r.is_json


def test_method_not_allowed_is_stable_json():
    c = _client()
    r = c.get("/api/account/login")
    assert r.status_code == 405
    assert r.get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_oversized_body_rejected_at_flask_boundary():
    c = _client(MAX_CONTENT_BYTES=1024)
    r = c.post("/api/account/register", json={"email": "x@y.com", "password": PW, "pad": "x" * 4096})
    assert r.status_code == 413
    assert r.get_json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_contracts_reject_invalid_shapes_before_llm_or_db():
    c = _client()
    c.post("/api/account/register", json={"email": "a@b.com", "password": PW})

    # practice attempt: unknown skill, impossible arithmetic
    assert c.post("/api/practice/attempt",
                  json={"skill": "hacking", "band": 7.0, "correct": 1, "total": 2}
                  ).status_code == 422
    assert c.post("/api/practice/attempt",
                  json={"skill": "reading", "band": 7.0, "correct": 9, "total": 2}
                  ).status_code == 422

    # mock scores must be IELTS half-bands in [0, 9]
    assert c.post("/api/mocks",
                  json={"listening": 6.0, "reading": 7.0, "overall": 7.3}
                  ).status_code == 422
    assert c.post("/api/mocks",
                  json={"listening": 12.0, "reading": 7.0, "overall": 6.5}
                  ).status_code == 422

    # vocab topic ceiling (LLM prompt input bound)
    assert c.post("/api/vocab", json={"topic": "x" * 300}).status_code == 422

    # SM-2 quality must be 0..5
    cid = c.post("/api/cards", json={"front": "word", "back": "meaning"}).get_json()["id"]
    assert c.post(f"/api/cards/{cid}/review", json={"quality": 99}).status_code == 422


# ── WS09-08: errors are stable, correlated, and leak nothing ─────────────────

def test_unhandled_exception_returns_json_without_stack_or_secrets():
    app = create_app(_overrides())

    @app.route("/api/_boom", methods=["GET"])
    def _boom():
        raise RuntimeError("provider key sk-SECRET-VALUE must never leak")

    r = app.test_client().get("/api/_boom")
    assert r.status_code == 500
    body = r.get_json()
    assert body["error"]["code"] == "INTERNAL"
    text = r.get_data(as_text=True)
    assert "SECRET-VALUE" not in text
    assert "Traceback" not in text
    assert "RuntimeError" not in text


def test_request_id_is_generated_and_echoed():
    c = _client()
    rid1 = c.get("/api/health").headers.get("X-Request-ID")
    assert rid1
    # a well-formed incoming id is preserved (support correlation)
    r2 = c.get("/api/health", headers={"X-Request-ID": "support-ticket-42"})
    assert r2.headers.get("X-Request-ID") == "support-ticket-42"
    # hostile ids are not reflected
    r3 = c.get("/api/health", headers={"X-Request-ID": "bad id <script>"})
    assert r3.headers.get("X-Request-ID") != "bad id <script>"


def test_error_payload_carries_request_id():
    c = _client()
    r = c.post("/api/account/login", json={"email": "nobody@x.com", "password": "wrong-pw-x"},
               headers={"X-Request-ID": "corr-1"})
    assert r.get_json()["error"]["requestId"] == "corr-1"


# ── WS09-10: health surfaces ─────────────────────────────────────────────────

def test_readiness_ok_with_db():
    c = _client()
    r = c.get("/api/health/ready")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True and body["checks"]["db"] is True


def test_readiness_fails_closed_without_leaking_topology():
    app = create_app(_overrides())

    class _BrokenSessionFactory:
        def __call__(self):
            raise RuntimeError("db connection failed")

    class _BrokenRepo:
        session_factory = _BrokenSessionFactory()

    app.config["REPO"] = _BrokenRepo()
    r = app.test_client().get("/api/health/ready")
    assert r.status_code == 503
    body = r.get_json()
    assert body["ok"] is False and body["checks"]["db"] is False
    assert "sqlite" not in r.get_data(as_text=True).lower()
    assert "RuntimeError" not in r.get_data(as_text=True)


def test_health_detail_is_admin_only():
    c = _client(ADMIN_EMAILS="admin@x.com")
    anon = c.get("/api/admin/health/detail")
    assert anon.status_code in (401, 403)
    c.post("/api/account/register", json={"email": "admin@x.com", "password": PW})
    r = c.get("/api/admin/health/detail")
    assert r.status_code == 200
    body = r.get_json()
    assert body["llmMode"] == "stub"
    assert body["providerConfigured"] is False

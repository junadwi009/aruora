"""WS03 — identity, session, and account security tests.

Maps to docs/production-readiness/03 §Security tests:
rotation, revocation, single-use reset tokens, CSRF rejection, generic
forgot-password responses, admin self-service denial, email-verification
gating, progressive brute-force throttling across shared-store "processes",
transparent rehash, mailer log safety, and fail-closed mail startup.
"""
import logging

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.kv import MemoryKV
from app.security import passwords, totp
from app.services import mailer
from app.services.llm import LlmGateway
from flask.testing import FlaskClient

STRONG = "correct horse battery staple"


def _make_app(**extra):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    repo = Repository(Session)
    o = {
        "TESTING": True,
        "SESSION_SECRET": "test-secret",
        "REPO": repo,
        "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
    }
    o.update(extra)
    return create_app(o), repo


def _client(**extra):
    app, repo = _make_app(**extra)
    return app.test_client(), app, repo


def _raw_client(**extra):
    """A client that does NOT auto-echo the CSRF header (forgery simulation)."""
    app, repo = _make_app(**extra)
    return FlaskClient(app, app.response_class), app, repo


def _register(c, email="u@x.com", password=STRONG):
    return c.post("/api/account/register", json={"email": email, "password": password})


# ── WS03-02: the session identifier rotates at authentication boundaries ─────

def test_session_id_rotates_on_login():
    c, _, _ = _client()
    _register(c)
    sid1 = c.get_cookie("ar_sid").value
    c.post("/api/account/logout")
    c.post("/api/account/login", json={"email": "u@x.com", "password": STRONG})
    sid2 = c.get_cookie("ar_sid").value
    assert sid1 and sid2 and sid1 != sid2


def test_old_session_id_is_invalid_after_rotation():
    c, _, _ = _client()
    _register(c)
    old = c.get_cookie("ar_sid").value
    c.post("/api/account/logout")
    c.post("/api/account/login", json={"email": "u@x.com", "password": STRONG})
    # Replay the OLD cookie: must not authenticate.
    c2 = FlaskClient(c.application, c.application.response_class)
    c2.set_cookie("ar_sid", old, domain="localhost")
    assert c2.get("/api/account/me").status_code == 401


# ── WS03-01: logout revokes server state; revocation is central ──────────────

def test_logout_invalidates_server_state():
    c, _, _ = _client()
    _register(c)
    cookie = c.get_cookie("ar_sid")
    c.post("/api/account/logout")
    assert c.get("/api/account/me").status_code == 401
    # The stored row is revoked, not merely the cookie dropped: replaying the
    # exact cookie must still fail.
    c.set_cookie("ar_sid", cookie.value, domain="localhost")
    assert c.get("/api/account/me").status_code == 401


def test_password_change_revokes_other_sessions():
    a, app, _ = _client()
    _register(a)
    b = FlaskClient(app, app.response_class)
    b.post("/api/account/login", json={"email": "u@x.com", "password": STRONG})
    assert b.get("/api/account/me").status_code == 200
    # Session A changes the password; session B must die, A survives.
    r = a.post("/api/account/password",
               json={"currentPassword": STRONG, "newPassword": "brand-new-passphrase-42"})
    assert r.status_code == 200
    assert a.get("/api/account/me").status_code == 200
    assert b.get("/api/account/me").status_code == 401


# ── WS03-06: stateful single-use reset tokens ────────────────────────────────

def _capture_reset_token(monkeypatch, c, email):
    sent = {}
    real = mailer.send_email

    def spy(cfg, to, subject, body):
        sent["to"], sent["body"] = to, body
        return True

    monkeypatch.setattr(mailer, "send_email", spy)
    c.post("/api/account/forgot", json={"email": email})
    monkeypatch.setattr(mailer, "send_email", real)
    import re

    m = re.search(r"reset_token=([\w.\-]+)", sent["body"])
    return m.group(1) if m else None


def test_reset_token_cannot_be_reused(monkeypatch):
    c, _, _ = _client()
    _register(c)
    c.post("/api/account/logout")
    token = _capture_reset_token(monkeypatch, c, "u@x.com")
    assert c.post("/api/account/reset",
                  json={"token": token, "newPassword": "brand-new-passphrase-42"}).status_code == 200
    # Second use of the same token must fail.
    assert c.post("/api/account/reset",
                  json={"token": token, "newPassword": "another-passphrase-42"}).status_code == 400


def test_password_reset_revokes_old_sessions(monkeypatch):
    a, app, _ = _client()
    _register(a)
    b = FlaskClient(app, app.response_class)
    b.post("/api/account/login", json={"email": "u@x.com", "password": STRONG})
    token = _capture_reset_token(monkeypatch, a, "u@x.com")
    assert a.post("/api/account/reset",
                  json={"token": token, "newPassword": "brand-new-passphrase-42"}).status_code == 200
    assert b.get("/api/account/me").status_code == 401


def test_forgot_response_is_generic(monkeypatch):
    c, _, _ = _client()
    _register(c, "known@x.com")
    bodies = {}
    real = mailer.send_email

    def spy(cfg, to, subject, body):
        bodies[to] = body
        return True

    monkeypatch.setattr(mailer, "send_email", spy)
    r1 = c.post("/api/account/forgot", json={"email": "known@x.com"})
    r2 = c.post("/api/account/forgot", json={"email": "unknown@x.com"})
    monkeypatch.setattr(mailer, "send_email", real)
    assert r1.status_code == r2.status_code == 200
    assert r1.get_json() == r2.get_json() == {"ok": True}


# ── WS03-03: CSRF ────────────────────────────────────────────────────────────

def test_forged_request_without_csrf_header_rejected():
    c, _, _ = _raw_client()
    _register(c)  # authenticated now
    r = c.post("/api/account/profile", json={"name": "Attacker"})
    assert r.status_code == 403
    assert r.get_json()["error"]["code"] == "CSRF_REJECTED"


def test_forged_request_with_wrong_csrf_token_rejected():
    c, _, _ = _raw_client()
    _register(c)
    r = c.post("/api/account/profile", json={"name": "Attacker"},
               headers={"X-CSRF-Token": "forged-token"})
    assert r.status_code == 403


def test_valid_csrf_token_is_accepted():
    c, _, _ = _raw_client()
    _register(c)
    token = c.get_cookie("ar_csrf").value
    r = c.patch("/api/account/profile", json={"name": "Learner"},
                headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    assert c.get("/api/account/me").get_json()["name"] == "Learner"


def test_cross_site_origin_rejected():
    c, _, _ = _raw_client()
    r = c.post("/api/account/login",
               json={"email": "u@x.com", "password": STRONG},
               headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert r.get_json()["error"]["code"] == "CSRF_REJECTED"


def test_same_site_origin_accepted():
    c, _, _ = _raw_client()
    r = c.post("/api/account/login",
               json={"email": "nobody@x.com", "password": STRONG},
               headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 401  # auth failure, NOT a CSRF rejection


# ── WS03-07: admin boundaries ────────────────────────────────────────────────

def test_user_cannot_self_assign_admin():
    c, repo, _ = _client()
    r = _register(c)
    assert r.get_json()["isAdmin"] is False
    # Profile updates cannot touch role/email/verified fields.
    c.patch("/api/account/profile",
            json={"name": "X", "isAdmin": True, "email": "root@x.com", "emailVerified": True})
    me = c.get("/api/account/me").get_json()
    assert me["isAdmin"] is False
    assert me["email"] == "u@x.com"
    assert me["emailVerified"] is False
    # No DB write grants admin either (no role column exists at all).
    assert c.get("/api/admin/users").status_code == 403


# ── WS03-05: email verification gate ─────────────────────────────────────────

def test_unverified_email_blocks_expensive_routes(monkeypatch):
    c, _, _ = _client(EMAIL_VERIFICATION_REQUIRED=True)
    _register(c)
    r = c.post("/api/reading/generate", json={"band": "B2"})
    assert r.status_code == 403
    assert r.get_json()["error"]["code"] == "EMAIL_UNVERIFIED"
    # Cheap routes and account management stay available.
    assert c.get("/api/account/me").status_code == 200


def test_verify_token_unlocks_expensive_routes(monkeypatch):
    c, _, _ = _client(EMAIL_VERIFICATION_REQUIRED=True)
    _register(c)
    token = _capture_verify_token(monkeypatch, c)
    assert c.post("/api/account/verify", json={"token": token}).status_code == 200
    assert c.get("/api/account/me").get_json()["emailVerified"] is True
    assert c.post("/api/reading/generate", json={"band": "B2"}).status_code == 200


def _capture_verify_token(monkeypatch, c):
    sent = {}
    real = mailer.send_email

    def spy(cfg, to, subject, body):
        sent["body"] = body
        return True

    monkeypatch.setattr(mailer, "send_email", spy)
    c.post("/api/account/verify/resend")
    monkeypatch.setattr(mailer, "send_email", real)
    import re

    m = re.search(r"verify_token=([\w.\-]+)", sent["body"])
    return m.group(1)


def test_verify_token_is_single_use(monkeypatch):
    c, _, _ = _client(EMAIL_VERIFICATION_REQUIRED=True)
    _register(c)
    token = _capture_verify_token(monkeypatch, c)
    assert c.post("/api/account/verify", json={"token": token}).status_code == 200
    assert c.post("/api/account/verify", json={"token": token}).status_code == 400


# ── WS03-08: shared-store abuse controls across "processes" ─────────────────

def test_brute_force_throttle_shared_across_two_app_instances():
    """Two app instances = two worker processes; one shared KV = one store."""
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    repo = Repository(Session)
    shared_kv = MemoryKV()  # stands in for the shared Redis
    apps = [
        create_app({"TESTING": True, "SESSION_SECRET": "test-secret",
                    "REPO": repo, "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
                    "KV": shared_kv})
        for _ in range(2)
    ]
    c1 = FlaskClient(apps[0], apps[0].response_class)
    c2 = FlaskClient(apps[1], apps[1].response_class)

    # 10 failures via process 1 exhaust the login budget (once progressive
    # backoff kicks in, later attempts answer 429 — that's the same control).
    for _ in range(10):
        r = c1.post("/api/account/login",
                    json={"email": "u@x.com", "password": "nope-not-it-12"})
        assert r.status_code in (401, 429)
    # ...process 2 must see the same exhausted budget (not a fresh counter).
    assert c2.post("/api/account/login",
                   json={"email": "u@x.com", "password": "nope-not-it-12"}).status_code == 429


def test_progressive_backoff_avoids_permanent_lockout():
    kv = MemoryKV()
    app, repo = None, None
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    repo = Repository(Session)
    app = create_app({"TESTING": True, "SESSION_SECRET": "test-secret",
                      "REPO": repo, "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
                      "KV": kv})
    c = FlaskClient(app, app.response_class)
    repo.create_account("v@x.com", STRONG)
    for _ in range(10):
        c.post("/api/account/login", json={"email": "v@x.com", "password": "wrong-pass-here"})
    # Backoff active → locked out for now...
    assert c.post("/api/account/login",
                  json={"email": "v@x.com", "password": STRONG}).status_code == 429
    # ...but the block decays (never permanent): expiry returns the key to None.
    kv._data.clear()  # simulate time passing beyond the backoff TTL
    assert c.post("/api/account/login",
                  json={"email": "v@x.com", "password": STRONG}).status_code == 200


# ── WS03-04: transparent rehash ──────────────────────────────────────────────

def test_legacy_hash_rehashes_on_login():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    repo = Repository(Session)
    from werkzeug.security import generate_password_hash as wz

    with Session() as s:
        from app.data.models import UserProfile

        s.add(UserProfile(name="L", goal="other", target_band=6.0, skill_targets={},
                          email="legacy@x.com", password_hash=wz(STRONG)))
        s.commit()
    app = create_app({"TESTING": True, "SESSION_SECRET": "test-secret",
                      "REPO": repo, "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"}))})
    c = FlaskClient(app, app.response_class)
    assert c.post("/api/account/login",
                  json={"email": "legacy@x.com", "password": STRONG}).status_code == 200
    u = repo.get_account_by_email("legacy@x.com")
    assert u.password_hash.startswith("$argon2" if passwords.HAVE_ARGON2 else "scrypt:")


# ── WS03-06B: mailer never leaks tokens; fail-closed startup ─────────────────

def test_mailer_logs_never_contain_tokens_or_urls(monkeypatch, caplog):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    repo = Repository(Session)
    app = create_app({"TESTING": True, "SESSION_SECRET": "test-secret",
                      "REPO": repo, "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"}))})
    c = app.test_client()  # CSRF-aware: forgot with a live session needs the header
    _register(c)
    with caplog.at_level(logging.WARNING):
        token = _capture_reset_token(monkeypatch, c, "u@x.com")
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert token and token not in joined
    assert "reset_token" not in joined
    assert "u@x.com" not in joined  # no raw recipient either
    # Bodies (even when SMTP is absent) are never logged at any level.
    assert STRONG not in joined


def test_production_fails_to_start_when_mail_flows_enabled_without_smtp():
    with pytest.raises(RuntimeError):
        create_app({
            "TESTING": False, "SESSION_SECRET": "x" * 40,
            "EMAIL_VERIFICATION_REQUIRED": True, "SMTP_HOST": "",
        })


def test_production_boots_when_mail_configured_or_flows_disabled():
    # Email flows disabled (default) → no SMTP requirement.
    create_app({"TESTING": False, "SESSION_SECRET": "x" * 40})


# ── WS03-07: TOTP ────────────────────────────────────────────────────────────

def test_totp_unit_and_admin_login():
    secret = totp.generate_secret()
    code = totp._code_at(secret, int(1700000000 // 30))
    assert totp.totp_verify(secret, code, at=1700000000)
    assert totp.totp_verify(secret, code, at=1700000000 + 30)  # ±1 step drift
    assert not totp.totp_verify(secret, "000000", at=1700000000) or code == "000000"
    assert not totp.totp_verify(secret, "abcdef", at=1700000000)

    c, _, repo = _client(
        ADMIN_TOTP_SECRET=secret,
        ADMIN_EMAILS="boss@x.com",
    )

    r = _register(c, "boss@x.com")
    uid = r.get_json()["id"]

    # Admin privilege only becomes eligible after verified ownership.
    repo.set_email_verified(uid, True)

    c.post("/api/account/logout")
    # Without the code: rejected.
    r = c.post("/api/account/login",
               json={"email": "boss@x.com", "password": STRONG})
    assert r.status_code == 401
    # With the current code: accepted.
    import time

    current = totp._code_at(secret, int(time.time() // 30))

    r = c.post(
        "/api/account/login",
        json={
            "email": "boss@x.com",
            "password": STRONG,
            "totp": current,
        },
    )

    assert r.status_code == 200
    assert r.get_json()["isAdmin"] is True

    # Proves MFA proof is bound to the resulting session.
    assert c.get("/api/admin/users").status_code == 200


# ── WS03-09: session-management UX ───────────────────────────────────────────

def test_sessions_list_and_logout_all():
    a, app, _ = _client()
    _register(a)
    b = FlaskClient(app, app.response_class)
    b.post("/api/account/login", json={"email": "u@x.com", "password": STRONG})
    rows = a.get("/api/account/sessions").get_json()
    assert len(rows) == 2
    assert sum(1 for r in rows if r["current"]) == 1
    r = a.delete("/api/account/sessions")
    assert r.status_code == 200
    # Every device is signed out, including the caller.
    assert a.get("/api/account/me").status_code == 401
    assert b.get("/api/account/me").status_code == 401


def test_logout_others_keeps_current_session():
    a, app, _ = _client()
    _register(a)
    b = FlaskClient(app, app.response_class)
    b.post("/api/account/login", json={"email": "u@x.com", "password": STRONG})
    assert a.delete("/api/account/sessions/others").status_code == 200
    assert a.get("/api/account/me").status_code == 200
    assert b.get("/api/account/me").status_code == 401

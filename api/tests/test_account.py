"""Phase 3a: account identity + auth + sliding session timeout."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.services.llm import LlmGateway


def _client(timeout_min=30):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    overrides = {
        "TESTING": True,
        "SESSION_SECRET": "test",
        "SESSION_TIMEOUT_MIN": timeout_min,
        "REPO": Repository(Session),
        "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
    }
    return create_app(overrides).test_client(), Repository(Session)


# ── Repository ───────────────────────────────────────────────────────────────

def test_repo_account_create_and_verify():
    from sqlalchemy import create_engine as ce
    eng = ce("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    repo = Repository(sessionmaker(bind=eng))
    u = repo.create_account("a@b.com", "correct horse battery staple", name="Arjuna")
    assert u.id is not None and u.email == "a@b.com"
    # password is hashed, not stored plaintext
    assert u.password_hash and u.password_hash != "correct horse battery staple"
    assert repo.verify_login("a@b.com", "correct horse battery staple") is not None
    assert repo.verify_login("a@b.com", "wrong") is None
    assert repo.get_account_by_email("a@b.com") is not None


# ── Routes ───────────────────────────────────────────────────────────────────

def test_register_login_me_logout():
    c, _ = _client()
    r = c.post("/api/account/register", json={"email": "x@y.com", "password": "correct horse battery staple"})
    assert r.status_code == 200 and r.get_json()["email"] == "x@y.com"

    me = c.get("/api/account/me")
    assert me.status_code == 200 and me.get_json()["email"] == "x@y.com"

    c.post("/api/account/logout")
    assert c.get("/api/account/me").status_code == 401

    li = c.post("/api/account/login", json={"email": "x@y.com", "password": "correct horse battery staple"})
    assert li.status_code == 200
    assert c.get("/api/account/me").status_code == 200


def test_duplicate_email_rejected():
    c, _ = _client()
    c.post("/api/account/register", json={"email": "dup@y.com", "password": "correct horse battery staple"})
    c.post("/api/account/logout")
    r = c.post("/api/account/register", json={"email": "dup@y.com", "password": "another-passphrase-42"})
    assert r.status_code == 422


def test_wrong_password_401():
    c, _ = _client()
    c.post("/api/account/register", json={"email": "z@y.com", "password": "correct horse battery staple"})
    c.post("/api/account/logout")
    assert c.post("/api/account/login", json={"email": "z@y.com", "password": "nope"}).status_code == 401


def test_remember_me_extends_timeout_to_seven_days(monkeypatch):
    import app.session as sess
    from datetime import timedelta
    real_now = sess._now

    c, _ = _client(timeout_min=30)
    c.post("/api/account/register", json={"email": "r@y.com", "password": "correct horse battery staple"})
    c.post("/api/account/logout")

    # Without remember: 31 min idle expires the session (as before).
    c.post("/api/account/login", json={"email": "r@y.com", "password": "correct horse battery staple"})
    monkeypatch.setattr(sess, "_now", lambda: real_now() + timedelta(minutes=31))
    assert c.get("/api/account/me").status_code == 401
    monkeypatch.setattr(sess, "_now", real_now)

    # With remember: 31 min idle is fine; 8 days idle forgets the session.
    c.post("/api/account/login", json={"email": "r@y.com", "password": "correct horse battery staple", "remember": True})
    monkeypatch.setattr(sess, "_now", lambda: real_now() + timedelta(minutes=31))
    assert c.get("/api/account/me").status_code == 200
    monkeypatch.setattr(sess, "_now", lambda: real_now() + timedelta(days=8))
    assert c.get("/api/account/me").status_code == 401


def test_idle_timeout_expires_session(monkeypatch):
    c, _ = _client(timeout_min=30)
    c.post("/api/account/register", json={"email": "t@y.com", "password": "correct horse battery staple"})
    assert c.get("/api/account/me").status_code == 200

    # Force the stored last_seen far into the past.
    import app.session as sess
    from datetime import datetime, timezone, timedelta
    real_now = sess._now
    monkeypatch.setattr(sess, "_now", lambda: real_now() + timedelta(minutes=31))
    r = c.get("/api/account/me")
    assert r.status_code == 401
    assert r.get_json()["error"]["code"] == "SESSION_EXPIRED"

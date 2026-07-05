"""Sign in with Google: verify an ID token, then find/create the user by google_sub."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.routes.account as account_routes
from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.services.llm import LlmGateway

CLAIMS = {"sub": "google-123", "email": "g@user.com", "name": "Gina", "email_verified": True}


def _client(client_id="test-client.apps.googleusercontent.com"):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    overrides = {
        "TESTING": True, "SESSION_SECRET": "test",
        "GOOGLE_CLIENT_ID": client_id,
        "REPO": Repository(Session),
        "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
    }
    return create_app(overrides).test_client(), Repository(Session)


def _stub_verify(monkeypatch, claims=CLAIMS):
    monkeypatch.setattr(account_routes, "verify_google_id_token", lambda token, cid: claims)


def test_google_login_creates_account_and_session(monkeypatch):
    _stub_verify(monkeypatch)
    c, _ = _client()
    r = c.post("/api/account/google", json={"credential": "fake-jwt"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["email"] == "g@user.com"
    # session established
    assert c.get("/api/account/me").status_code == 200


def test_google_login_is_idempotent_by_sub(monkeypatch):
    _stub_verify(monkeypatch)
    c, repo = _client()
    id1 = c.post("/api/account/google", json={"credential": "x"}).get_json()["id"]
    c.post("/api/account/logout")
    id2 = c.post("/api/account/google", json={"credential": "x"}).get_json()["id"]
    assert id1 == id2  # same google_sub → same user, no duplicate


def test_google_links_to_existing_email_account(monkeypatch):
    _stub_verify(monkeypatch)
    c, repo = _client()
    existing = repo.create_account("g@user.com", "secret123")  # password account, same email
    got = c.post("/api/account/google", json={"credential": "x"}).get_json()
    assert got["id"] == existing.id  # linked, not duplicated


def test_google_unverified_email_not_adopted(monkeypatch):
    """An unverified Google email must not be trusted/adopted (anti-takeover)."""
    _stub_verify(monkeypatch, claims={
        "sub": "google-999", "email": "unv@user.com", "name": "U", "email_verified": False,
    })
    c, _ = _client()
    body = c.post("/api/account/google", json={"credential": "x"}).get_json()
    # Signed in by sub, but the unverified email is NOT adopted.
    assert body["email"] is None


def test_invalid_google_token_401(monkeypatch):
    monkeypatch.setattr(account_routes, "verify_google_id_token", lambda token, cid: None)
    c, _ = _client()
    assert c.post("/api/account/google", json={"credential": "bad"}).status_code == 401


def test_google_not_configured_501(monkeypatch):
    _stub_verify(monkeypatch)
    c, _ = _client(client_id="")  # GOOGLE_CLIENT_ID empty
    assert c.post("/api/account/google", json={"credential": "x"}).status_code == 501


def test_health_exposes_google_client_id():
    c, _ = _client(client_id="abc.apps.googleusercontent.com")
    assert c.get("/api/health").get_json()["googleClientId"] == "abc.apps.googleusercontent.com"

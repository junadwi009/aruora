"""Master-admin (Manage users).

Admin is designated server-side via ADMIN_EMAILS — never self-service. A request
is admin iff the signed-in account's email is in that set. No is_admin column, so
admin can't be granted by a DB write — only by deployment config.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.services.llm import LlmGateway

ADMIN = "boss@x.com"


def _client(admin_emails=ADMIN):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    overrides = {
        "TESTING": True,
        "SESSION_SECRET": "test",
        "ADMIN_EMAILS": admin_emails,
        "REPO": Repository(Session),
        "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
    }
    return create_app(overrides).test_client(), Repository(Session)


def _register(c, email, password="secret123"):
    return c.post("/api/account/register", json={"email": email, "password": password})


# ── Config ───────────────────────────────────────────────────────────────────

def test_config_parses_admin_emails_csv():
    cfg = Config({"ADMIN_EMAILS": "A@x.com, b@Y.com ,"})
    assert cfg.ADMIN_EMAILS == frozenset({"a@x.com", "b@y.com"})


def test_config_admin_emails_empty_by_default():
    assert Config({}).ADMIN_EMAILS == frozenset()


# ── isAdmin flag on the account ──────────────────────────────────────────────

def test_me_includes_is_admin_flag():
    c, _ = _client()
    _register(c, ADMIN)
    assert c.get("/api/account/me").get_json()["isAdmin"] is True

    c.post("/api/account/logout")
    _register(c, "normal@x.com")
    assert c.get("/api/account/me").get_json()["isAdmin"] is False


# ── Gating ───────────────────────────────────────────────────────────────────

def test_admin_endpoints_require_login():
    c, _ = _client()
    assert c.get("/api/admin/users").status_code == 401


def test_non_admin_forbidden():
    c, _ = _client()
    _register(c, "normal@x.com")
    assert c.get("/api/admin/users").status_code == 403
    assert c.get("/api/admin/stats").status_code == 403


# ── Manage users ─────────────────────────────────────────────────────────────

def test_admin_lists_accounts():
    c, _ = _client()
    _register(c, "alice@x.com")
    c.post("/api/account/logout")
    _register(c, ADMIN)
    r = c.get("/api/admin/users")
    assert r.status_code == 200
    emails = {u["email"] for u in r.get_json()}
    assert {"alice@x.com", ADMIN} <= emails


def test_admin_stats():
    c, _ = _client()
    _register(c, "alice@x.com")
    c.post("/api/account/logout")
    _register(c, ADMIN)
    s = c.get("/api/admin/stats").get_json()
    assert s["totalAccounts"] >= 2
    assert "totalAttempts" in s


def test_admin_deletes_user_but_not_self():
    c, _ = _client()
    rid = _register(c, "victim@x.com").get_json()["id"]
    c.post("/api/account/logout")
    me = _register(c, ADMIN).get_json()

    # delete another user → gone
    assert c.delete(f"/api/admin/users/{rid}").status_code == 200
    assert "victim@x.com" not in {u["email"] for u in c.get("/api/admin/users").get_json()}

    # can't delete self via the admin endpoint
    assert c.delete(f"/api/admin/users/{me['id']}").status_code == 400


def test_admin_triggers_password_reset():
    c, _ = _client()
    rid = _register(c, "alice@x.com").get_json()["id"]
    c.post("/api/account/logout")
    _register(c, ADMIN)
    assert c.post(f"/api/admin/users/{rid}/reset-password").status_code == 200


def test_non_admin_cannot_delete():
    c, _ = _client()
    rid = _register(c, "alice@x.com").get_json()["id"]
    c.post("/api/account/logout")
    _register(c, "normal@x.com")
    assert c.delete(f"/api/admin/users/{rid}").status_code == 403

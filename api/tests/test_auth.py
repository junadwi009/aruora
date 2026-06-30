"""Phase 2e-1: optional passcode gate. Disabled when APP_PASSCODE is empty."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.services.llm import LlmGateway


def _client(passcode=""):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    overrides = {
        "TESTING": True,
        "APP_PASSCODE": passcode,
        "SESSION_SECRET": "test-secret",
        "REPO": Repository(Session),
        "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
    }
    return create_app(overrides).test_client()


def test_auth_disabled_when_no_passcode():
    c = _client(passcode="")
    assert c.get("/api/auth/status").get_json()["authRequired"] is False
    # protected route is open
    assert c.get("/api/skill-levels").status_code == 200


def test_auth_gate_blocks_then_allows():
    c = _client(passcode="1234")
    status = c.get("/api/auth/status").get_json()
    assert status["authRequired"] is True and status["authenticated"] is False

    # health + auth endpoints stay open
    assert c.get("/api/health").status_code == 200

    # protected route blocked
    assert c.get("/api/skill-levels").status_code == 401

    # wrong passcode
    assert c.post("/api/auth/login", json={"passcode": "nope"}).status_code == 401
    # correct passcode → session cookie set
    assert c.post("/api/auth/login", json={"passcode": "1234"}).status_code == 200

    # now authenticated
    assert c.get("/api/auth/status").get_json()["authenticated"] is True
    assert c.get("/api/skill-levels").status_code == 200

    # logout revokes
    c.post("/api/auth/logout")
    assert c.get("/api/skill-levels").status_code == 401

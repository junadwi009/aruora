"""
Shared pytest fixtures for IELTS Coach API tests.
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


@pytest.fixture
def client_with_seed():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    repo = Repository(Session)
    gw = LlmGateway(Config({"LLM_MODE": "stub"}))
    app = create_app({"TESTING": True, "REPO": repo, "GATEWAY": gw})
    client = app.test_client()
    # Establish a signed-in session so data routes are scoped to a real user
    # (multi-user, Phase 3b). Tests that need their own user can register again.
    client.post("/api/account/register", json={"email": "tester@example.com", "password": "secret123"})
    return client

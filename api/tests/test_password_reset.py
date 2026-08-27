"""Phase 4-auth: SMTP-optional forgot/reset password."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.services.llm import LlmGateway
from app.services import mailer


def _ctx():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    repo = Repository(Session)
    app = create_app({
        "TESTING": True, "SESSION_SECRET": "test-secret",
        "REPO": repo, "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
    })
    return app.test_client(), repo


def test_forgot_always_200_even_unknown_email(monkeypatch):
    client, _ = _ctx()
    sent = {}
    monkeypatch.setattr(mailer, "send_email", lambda cfg, to, subj, body: sent.update(to=to, body=body) or True)
    # unknown email — still 200 (no enumeration)
    assert client.post("/api/account/forgot", json={"email": "nobody@x.com"}).status_code == 200
    assert "to" not in sent  # nothing sent for unknown account


def test_forgot_then_reset(monkeypatch):
    client, repo = _ctx()
    repo.create_account("u@x.com", "old-password-fallback-42")
    captured = {}
    monkeypatch.setattr(mailer, "send_email",
                        lambda cfg, to, subj, body: captured.update(to=to, body=body) or True)

    assert client.post("/api/account/forgot", json={"email": "u@x.com"}).status_code == 200
    assert captured["to"] == "u@x.com"
    # the email body carries the reset token
    import re
    m = re.search(r"reset_token=([\w.\-]+)", captured["body"])
    assert m, "reset token missing from email body"
    token = m.group(1)

    # reset with the token
    r = client.post("/api/account/reset", json={"token": token, "newPassword": "new-password-fallback-42"})
    assert r.status_code == 200
    # old password fails, new one works
    assert repo.verify_login("u@x.com", "old-password-fallback-42") is None
    assert repo.verify_login("u@x.com", "new-password-fallback-42") is not None


def test_reset_bad_token_400():
    client, _ = _ctx()
    assert client.post("/api/account/reset", json={"token": "garbage", "newPassword": "new-password-fallback-42"}).status_code == 400

"""Phase 4a: study reminders (cron-triggerable, SMTP-optional)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.services.llm import LlmGateway
from app.services import mailer


def _ctx(token="cron-secret"):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    repo = Repository(sessionmaker(bind=eng))
    app = create_app({
        "TESTING": True, "SESSION_SECRET": "x", "REMINDER_TOKEN": token,
        "REPO": repo, "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
    })
    return app.test_client(), repo


def test_repo_due_reminders():
    _, repo = _ctx()
    u = repo.create_account("a@e.com", "secret123")
    repo.update_profile(u.id, {"reminderTime": "09:00"})
    # due at hour 9, not sent today
    due = repo.due_reminders(hour=9, today="2026-06-30")
    assert any(d["email"] == "a@e.com" for d in due)
    # not due at a different hour
    assert repo.due_reminders(hour=10, today="2026-06-30") == []


def test_run_endpoint_requires_token():
    client, _ = _ctx(token="cron-secret")
    assert client.post("/api/internal/reminders/run").status_code == 401
    assert client.post("/api/internal/reminders/run", headers={"X-Reminder-Token": "wrong"}).status_code == 401


def test_run_sends_once_per_day(monkeypatch):
    client, repo = _ctx(token="cron-secret")
    u = repo.create_account("a@e.com", "secret123")
    repo.update_profile(u.id, {"reminderTime": "09:00"})
    sent = []
    monkeypatch.setattr(mailer, "send_email", lambda cfg, to, s, b: sent.append(to) or True)

    hdr = {"X-Reminder-Token": "cron-secret"}
    r1 = client.post("/api/internal/reminders/run?hour=9&today=2026-06-30", headers=hdr)
    assert r1.status_code == 200 and r1.get_json()["sent"] == 1
    assert sent == ["a@e.com"]
    # second run same day → already sent → 0
    r2 = client.post("/api/internal/reminders/run?hour=9&today=2026-06-30", headers=hdr)
    assert r2.get_json()["sent"] == 0

"""Phase 4a study reminders — now timezone-aware (per-user reminder_tz)."""
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.services.llm import LlmGateway
from app.services import mailer

UTC = timezone.utc


def _ctx(token="cron-secret"):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    repo = Repository(sessionmaker(bind=eng))
    app = create_app({
        "TESTING": True, "SESSION_SECRET": "x", "REMINDER_TOKEN": token,
        "REPO": repo, "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
    })
    return app.test_client(), repo


# ── Repository: local-hour matching ──────────────────────────────────────────

def test_due_reminders_uses_user_timezone():
    _, repo = _ctx()
    u = repo.create_account("a@e.com", "correct horse battery staple")
    repo.update_profile(u.id, {"reminderTime": "09:00", "reminderTz": "Asia/Jakarta"})
    # 02:00 UTC == 09:00 in Asia/Jakarta (UTC+7) → due, local date attached
    due = repo.due_reminders(datetime(2026, 6, 30, 2, 0, tzinfo=UTC), "UTC")
    assert [d["email"] for d in due] == ["a@e.com"]
    assert due[0]["date"] == "2026-06-30"
    # 09:00 UTC == 16:00 Jakarta → not due
    assert repo.due_reminders(datetime(2026, 6, 30, 9, 0, tzinfo=UTC), "UTC") == []


def test_due_reminders_falls_back_to_default_tz():
    _, repo = _ctx()
    u = repo.create_account("b@e.com", "correct horse battery staple")
    repo.update_profile(u.id, {"reminderTime": "09:00"})  # no per-user tz
    now = datetime(2026, 6, 30, 2, 0, tzinfo=UTC)
    # default Asia/Jakarta → local 09:00 → due
    assert any(d["email"] == "b@e.com" for d in repo.due_reminders(now, "Asia/Jakarta"))
    # default UTC → local 02:00 → not due
    assert repo.due_reminders(now, "UTC") == []


def test_two_users_different_timezones():
    _, repo = _ctx()
    ja = repo.create_account("ja@e.com", "correct horse battery staple")
    repo.update_profile(ja.id, {"reminderTime": "09:00", "reminderTz": "Asia/Jakarta"})
    ny = repo.create_account("ny@e.com", "correct horse battery staple")
    repo.update_profile(ny.id, {"reminderTime": "09:00", "reminderTz": "America/New_York"})
    # 02:00 UTC = 09:00 Jakarta but ~22:00 (prev day) New York → only Jakarta due
    due = repo.due_reminders(datetime(2026, 6, 30, 2, 0, tzinfo=UTC), "UTC")
    assert {d["email"] for d in due} == {"ja@e.com"}


def test_invalid_tz_falls_back_to_default():
    _, repo = _ctx()
    u = repo.create_account("c@e.com", "correct horse battery staple")
    repo.update_profile(u.id, {"reminderTime": "09:00", "reminderTz": "Not/AZone"})
    now = datetime(2026, 6, 30, 2, 0, tzinfo=UTC)
    assert any(d["email"] == "c@e.com" for d in repo.due_reminders(now, "Asia/Jakarta"))


# ── Endpoint ─────────────────────────────────────────────────────────────────

def test_run_endpoint_requires_token():
    client, _ = _ctx(token="cron-secret")
    assert client.post("/api/internal/reminders/run").status_code == 401
    assert client.post("/api/internal/reminders/run", headers={"X-Reminder-Token": "wrong"}).status_code == 401


def test_run_sends_once_per_local_day(monkeypatch):
    client, repo = _ctx(token="cron-secret")
    u = repo.create_account("a@e.com", "correct horse battery staple")
    repo.update_profile(u.id, {"reminderTime": "09:00", "reminderTz": "Asia/Jakarta"})
    sent = []
    monkeypatch.setattr(mailer, "send_email", lambda cfg, to, s, b: sent.append(to) or True)

    hdr = {"X-Reminder-Token": "cron-secret"}
    # 02:00 UTC == 09:00 Jakarta
    r1 = client.post("/api/internal/reminders/run?now=2026-06-30T02:00:00Z", headers=hdr)
    assert r1.status_code == 200 and r1.get_json()["sent"] == 1
    assert sent == ["a@e.com"]
    # second run same local day → already sent → 0
    r2 = client.post("/api/internal/reminders/run?now=2026-06-30T02:00:00Z", headers=hdr)
    assert r2.get_json()["sent"] == 0

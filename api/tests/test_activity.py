"""Phase 4b: activity streak derived from attempts."""
from datetime import date, datetime, timezone, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.data.models import Base, Attempt
from app.data.repositories import Repository


def _repo():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Repository(sessionmaker(bind=eng))


def _add(repo, uid, when):
    with repo._sf() as s:
        a = Attempt(user_id=uid, type="writing", bands={"overall": 6.0})
        a.created_at = when
        s.add(a)
        s.commit()


def test_empty_streak():
    repo = _repo()
    uid = repo.create_account("a@e.com", "secret123").id
    assert repo.activity_stats(uid, date(2026, 6, 30)) == {"current": 0, "longest": 0, "today": 0, "daysActive": 0}


def test_three_day_streak():
    repo = _repo()
    uid = repo.create_account("a@e.com", "secret123").id
    today = date(2026, 6, 30)
    for delta in (0, 1, 2):  # today, yesterday, day before
        _add(repo, uid, datetime(2026, 6, 30, tzinfo=timezone.utc) - timedelta(days=delta))
    st = repo.activity_stats(uid, today)
    assert st["current"] == 3
    assert st["longest"] >= 3
    assert st["today"] == 1
    assert st["daysActive"] == 3


def test_streak_broken_yesterday_only():
    repo = _repo()
    uid = repo.create_account("a@e.com", "secret123").id
    today = date(2026, 6, 30)
    # active 2 days ago only → current streak 0 (gap), but daysActive 1
    _add(repo, uid, datetime(2026, 6, 28, tzinfo=timezone.utc))
    st = repo.activity_stats(uid, today)
    assert st["current"] == 0
    assert st["daysActive"] == 1

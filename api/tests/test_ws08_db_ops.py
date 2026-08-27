"""WS08 — database operations tests.

Covers:
- WS08-04B: production config validation fails closed on development
  defaults (default DB credentials, non-PostgreSQL backend);
- WS08-03: engine/pool kwargs for SQLite vs PostgreSQL profiles;
- WS08-08: the data-lifecycle sweep purges ONLY dead security/operational
  state and never touches learner history; the manual endpoint is
  token-guarded (fail closed when unset).
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from app.config import Config
from app.data.db import engine_kwargs


# ── WS08-04B: production configuration invariants ────────────────────────────

def _prod_overrides(**extra):
    base = {
        "TESTING": False,
        "APP_ENV": "production",
        "SESSION_SECRET": "p" * 48,
        "REDIS_URL": "",
    }
    base.update(extra)
    return base


def test_production_rejects_default_db_credentials():
    from app import create_app

    with pytest.raises(RuntimeError, match="WS08-04B"):
        create_app(overrides=_prod_overrides(
            DATABASE_URL="postgresql+psycopg://ielts:ielts@db:5432/ielts",
        ))


def test_production_rejects_placeholder_runtime_credential():
    from app import create_app

    with pytest.raises(RuntimeError, match="WS08-04B"):
        create_app(overrides=_prod_overrides(
            DATABASE_URL="postgresql+psycopg://app:change-me-strong@db:5432/ielts",
        ))


def test_production_rejects_non_postgresql_backend():
    from app import create_app

    with pytest.raises(RuntimeError, match="PostgreSQL"):
        create_app(overrides=_prod_overrides(DATABASE_URL="sqlite:///dev.db"))


def test_development_defaults_still_allowed_outside_production():
    """Without APP_ENV=production the convenience defaults keep working
    (disposable local development) — only the session-secret check applies."""
    from alembic import command
    from alembic.config import Config as AlembicConfig

    from app import create_app
    from app.data import db as db_mod

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = "sqlite+pysqlite:///" + path.replace("\\", "/")
    try:
        # Boot happens against a MIGRATED database (prod runs alembic first).
        cfg = AlembicConfig(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations"))
        old = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = url
        command.upgrade(cfg, "head")
        if old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old

        app = create_app(overrides={
            "TESTING": True,
            "APP_ENV": "development",
            "DATABASE_URL": url,
            "REDIS_URL": "",
        })
        assert app.config["APP_CONFIG"].APP_ENV == "development"
    finally:
        db_mod.dispose_engine()
        if os.path.exists(path):
            os.remove(path)


# ── WS08-03: engine/pool management ──────────────────────────────────────────

def test_sqlite_profile_keeps_defaults():
    kw = engine_kwargs("sqlite+pysqlite:///:memory:")
    assert kw == {"pool_pre_ping": True}


def test_postgres_profile_has_pool_and_timeout_guards(monkeypatch):
    monkeypatch.setenv("DB_STATEMENT_TIMEOUT_MS", "30000")
    kw = engine_kwargs("postgresql+psycopg://u:p@db:5432/aruora")
    assert kw["pool_pre_ping"] is True
    assert kw["pool_size"] >= 1
    assert kw["max_overflow"] >= 0
    assert kw["connect_args"]["connect_timeout"] >= 1
    assert "statement_timeout=30000" in kw["connect_args"]["options"]


def test_statement_timeout_disabled_by_default():
    kw = engine_kwargs("postgresql+psycopg://u:p@db:5432/aruora")
    assert "options" not in kw["connect_args"]


def test_bad_env_int_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("DB_POOL_SIZE", "not-a-number")
    kw = engine_kwargs("postgresql+psycopg://u:p@db:5432/aruora")
    assert kw["pool_size"] == 5


# ── WS08-08: data lifecycle maintenance ──────────────────────────────────────

@pytest.fixture(scope="module")
def maint_app():
    from alembic import command
    from alembic.config import Config as AlembicConfig

    from app import create_app
    from app.data import db as db_mod

    api_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = "sqlite+pysqlite:///" + path.replace("\\", "/")
    # Boot happens against a MIGRATED database (prod runs alembic first).
    cfg = AlembicConfig(os.path.join(api_root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(api_root, "migrations"))
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    command.upgrade(cfg, "head")
    if old is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = old
    app = create_app(overrides={
        "TESTING": True,
        "DATABASE_URL": url,
        "REDIS_URL": "",
        "SESSION_RETENTION_HOURS": "0",
        "OTT_RETENTION_HOURS": "0",
        "ANALYTICS_RETENTION_DAYS": "0",
        "JOB_RETENTION_HOURS": "0",
        "MAINTENANCE_TOKEN": "ws08-test-token",
    })
    yield app
    from app.data import db as db_mod

    db_mod.dispose_engine()
    if os.path.exists(path):
        os.remove(path)


def _seed_dead_and_live_rows(repo, now):
    """One dead row per purge target + protected live/learning rows."""
    from app.data.models import (
        AnalyticsEvent, Attempt, AuthOneTimeToken, AuthSession, Job,
        UserProfile,
    )

    old = now - timedelta(days=30)
    with repo.session_factory() as s:
        u = UserProfile(name="m", goal="work", target_band=6.5,
                        skill_targets={}, created_at=now)
        s.add(u)
        s.commit()
        uid = u.id

        # DEAD: revoked session past retention.
        s.add(AuthSession(id="dead0" * 8, user_id=uid, csrf_token="c",
                          flags={}, remember=False, device="", ip_hash="",
                          created_at=old, last_seen_at=old,
                          absolute_expires_at=now + timedelta(hours=1),
                          revoked_at=old))
        # LIVE: active (never revoked, absolute expiry in the future).
        s.add(AuthSession(id="live0" * 8, user_id=uid, csrf_token="c",
                          flags={}, remember=False, device="", ip_hash="",
                          created_at=now, last_seen_at=now,
                          absolute_expires_at=now + timedelta(hours=1)))
        # DEAD: expired one-time token.
        s.add(AuthOneTimeToken(kind="reset", user_id=uid, token_hash="t" * 64,
                               created_at=old, expires_at=old))
        # DEAD: finished job past retention.
        s.add(Job(id="11111111-1111-1111-1111-111111111111", user_id=None,
                  type="t", status="succeeded", created_at=old,
                  expires_at=old))
        # DEAD: raw analytics past retention.
        s.add(AnalyticsEvent(event_id="e-old", user_id=None, name="x",
                             occurred_at=old, properties={}))
        # PROTECTED: learner history must survive every purge.
        s.add(Attempt(user_id=uid, type="writing", task="task2", prompt="",
                      body="essay", bands={}, criteria={}, cefr="B2",
                      metrics={}, created_at=old))
        s.commit()
    return uid


def test_maintenance_sweep_purges_only_dead_state(maint_app):
    from app.data.models import (
        AnalyticsEvent, Attempt, AuthOneTimeToken, AuthSession, Job,
    )
    from app.jobs.maintenance import run_maintenance

    repo = maint_app.config["REPO"]
    cfg = maint_app.config["APP_CONFIG"]
    now = datetime.now(timezone.utc)
    uid = _seed_dead_and_live_rows(repo, now)

    counts = run_maintenance(repo, cfg, now=now)
    assert counts["sessions"] >= 1
    assert counts["one_time_tokens"] >= 1
    assert counts["jobs"] >= 1
    assert counts["analytics_events"] >= 1

    with repo.session_factory() as s:
        # dead rows gone
        assert s.get(AuthSession, "dead0" * 8) is None
        assert s.query(AuthOneTimeToken).count() == 0
        assert s.query(Job).count() == 0
        assert s.query(AnalyticsEvent).count() == 0
        # live session and ALL learner history survive
        assert s.get(AuthSession, "live0" * 8) is not None
        assert s.query(Attempt).filter(Attempt.user_id == uid).count() == 1


def test_maintenance_endpoint_requires_token(maint_app):
    client = maint_app.test_client()
    resp = client.post("/api/internal/maintenance/run")
    assert resp.status_code == 401
    resp = client.post("/api/internal/maintenance/run",
                       headers={"X-Maintenance-Token": "wrong"})
    assert resp.status_code == 401


def test_maintenance_endpoint_runs_with_token(maint_app):
    client = maint_app.test_client()
    resp = client.post("/api/internal/maintenance/run",
                       headers={"X-Maintenance-Token": "ws08-test-token"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert set(body["purged"]) == {
        "sessions", "one_time_tokens", "jobs", "analytics_events",
    }


def test_maintenance_endpoint_disabled_without_token(maint_app):
    """Empty MAINTENANCE_TOKEN = fail closed (endpoint disabled)."""
    cfg = Config({"MAINTENANCE_TOKEN": ""})
    assert cfg.MAINTENANCE_TOKEN == ""
    from app.routes.internal import run_maintenance  # noqa: F401  (route wired)

    client = maint_app.test_client()
    cfg_obj = maint_app.config["APP_CONFIG"]
    saved = cfg_obj.MAINTENANCE_TOKEN
    cfg_obj.MAINTENANCE_TOKEN = ""
    try:
        resp = client.post("/api/internal/maintenance/run",
                           headers={"X-Maintenance-Token": "anything"})
        assert resp.status_code == 401
    finally:
        cfg_obj.MAINTENANCE_TOKEN = saved

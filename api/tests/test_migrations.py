"""Migration tests (AGENTS.md: schema changes require migrations + migration tests).

Runs the full Alembic chain against a disposable SQLite database and asserts
the WS02-03 scoring-metadata columns exist on ``attempts``.
"""

import os
import tempfile

import pytest

alembic = pytest.importorskip("alembic")
from alembic import command  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from sqlalchemy import create_engine, inspect, text  # noqa: E402

API_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _alembic_config(db_url: str) -> AlembicConfig:
    cfg = AlembicConfig(os.path.join(API_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(API_ROOT, "migrations"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture(scope="module")
def migrated_engine():
    """Apply every migration to a temp SQLite DB and yield its engine."""
    from app.data import db as db_mod

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    # Windows absolute paths need forward slashes in a SQLAlchemy URL
    url = "sqlite+pysqlite:///" + path.replace("\\", "/")
    # migrations/env.py reads DATABASE_URL itself and overrides ini options
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        command.upgrade(_alembic_config(url), "head")
        engine = create_engine(url)
        yield engine
        engine.dispose()
    finally:
        if old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old
        # Boot tests leave the process-global engine on this file (Windows
        # refuses to delete an open SQLite file) — dispose it first.
        db_mod.dispose_engine()
        if os.path.exists(path):
            os.remove(path)


def test_migrations_apply_to_head(migrated_engine):
    insp = inspect(migrated_engine)
    tables = set(insp.get_table_names())
    assert "attempts" in tables
    assert "user_profile" in tables


def test_attempts_has_scoring_metadata_columns(migrated_engine):
    """WS02-03 columns are created by migration a4f7c2d91e05."""
    cols = {c["name"] for c in inspect(migrated_engine).get_columns("attempts")}
    expected = {
        "score_method",
        "score_version",
        "model_provider",
        "model_id",
        "prompt_version",
        "rubric_version",
        "calibration_version",
    }
    missing = expected - cols
    assert not missing, f"missing scoring metadata columns: {missing}"


def test_scoring_metadata_columns_are_nullable(migrated_engine):
    """Backward compatibility: pre-existing rows keep working (nullable)."""
    insp = inspect(migrated_engine)
    nullable = {c["name"]: c["nullable"] for c in insp.get_columns("attempts")}
    for col in ("score_method", "model_id", "calibration_version"):
        assert nullable[col] is True


def test_attempt_row_with_metadata_roundtrips(migrated_engine):
    """Insert + read back through raw SQL to confirm real persistence."""
    with migrated_engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO user_profile (name, goal, target_band, skill_targets, created_at) "
            "VALUES ('t', 'work', 6.5, '{}', CURRENT_TIMESTAMP)"
        ))
        uid = conn.execute(
            text("SELECT id FROM user_profile WHERE name = 't'")
        ).scalar_one()
        conn.execute(text(
            "INSERT INTO attempts (user_id, type, task, prompt, body, bands, criteria,"
            " cefr, metrics, score_method, score_version, model_provider, model_id,"
            " prompt_version, rubric_version, calibration_version, created_at)"
            " VALUES (:uid, 'writing', 'task2', '', 'x', '{}', '{}', 'B2', '{}',"
            " 'llm_estimate', '1.0', 'openrouter', 'test/model-1',"
            " '1.0', '1.0', '1.0', CURRENT_TIMESTAMP)"
        ), {"uid": uid})
        row = conn.execute(text(
            "SELECT model_id, score_method FROM attempts WHERE user_id = :uid"
        ), {"uid": uid}).fetchone()
    assert row.model_id == "test/model-1"
    assert row.score_method == "llm_estimate"


# ── WS04: ownership invariants hold after the full chain ──────────────────────

def _raw_sqlite_fks(conn, table):
    return conn.execute(text(f"PRAGMA foreign_key_list({table})")).fetchall()


def test_attempts_user_id_is_not_null_and_cascades(migrated_engine):
    """WS04-02/04 on the migrated schema itself."""
    with migrated_engine.connect() as conn:
        fks = _raw_sqlite_fks(conn, "attempts")
        # PRAGMA columns: (id, seq, table, from, to, on_update, on_delete)
        vals = [(f[3], f[6]) for f in fks
                if f[2] == "user_profile" and f[3] == "user_id"]
        assert vals, "attempts.user_id FK missing"
        assert all(v[1].upper() == "CASCADE" for v in vals), \
            f"expected CASCADE on attempts.user_id, got {vals}"


def test_account_deletion_cascades_everything(migrated_engine):
    """Deleting a profile removes ALL owned rows by schema design (WS04-04/07)."""
    with migrated_engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO user_profile (name, goal, target_band, skill_targets, created_at) "
            "VALUES ('victim', 'work', 6.5, '{}', CURRENT_TIMESTAMP)"
        ))
        uid = conn.execute(
            text("SELECT id FROM user_profile WHERE name = 'victim'")
        ).scalar_one()
        conn.execute(text(
            "INSERT INTO attempts (user_id, type, task, prompt, body, bands, criteria,"
            " cefr, metrics, created_at) "
            "VALUES (:u, 'writing', 'task2', '', 'x', '{}', '{}', 'B2', '{}',"
            " CURRENT_TIMESTAMP)"
        ), {"u": uid})
        conn.execute(text(
            "INSERT INTO mocks (user_id, listening, reading, overall, created_at) "
            "VALUES (:u, 0, 0, 0, CURRENT_TIMESTAMP)"
        ), {"u": uid})
        conn.execute(text(
            "INSERT INTO cards (user_id, front, back, ease, interval, reps, lapses,"
            " due, created_at) "
            "VALUES (:u, 'f', 'b', 2.5, 0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ), {"u": uid})
        conn.execute(text(
            "INSERT INTO programs (user_id, length_days, status, start_date) "
            "VALUES (:u, 30, 'active', CURRENT_TIMESTAMP)"
        ), {"u": uid})
        pid = conn.execute(text("SELECT id FROM programs WHERE user_id = :u"),
                           {"u": uid}).scalar_one()
        conn.execute(text(
            "INSERT INTO milestones (program_id, idx, day_target, title, targets) "
            "VALUES (:p, 0, 15, 'halfway', '{}')"
        ), {"p": pid})
        conn.execute(text("DELETE FROM user_profile WHERE id = :u"), {"u": uid})

    with migrated_engine.connect() as conn:
        # After the profile is gone, NO owned row may survive anywhere
        # (including rows of other users that must stay untouched).
        orphan_checks = {
            "attempts": "user_id",
            "mocks": "user_id",
            "cards": "user_id",
            "programs": "user_id",
            "skill_levels": "user_id",
            "placement_attempts": "user_id",
            "feedback": "user_id",
            "gen_usage": "user_id",
            "lessons": "user_id",
            "test_gate": "user_id",
        }
        orphans = {}
        for tbl, col in orphan_checks.items():
            n = conn.execute(text(
                f"SELECT COUNT(*) FROM {tbl} "
                f"WHERE {col} IS NOT NULL AND {col} NOT IN "
                "(SELECT id FROM user_profile)"
            )).scalar_one()
            orphans[tbl] = n
        # milestones are orphaned through their parent program chain
        n_ms = conn.execute(text(
            "SELECT COUNT(*) FROM milestones WHERE program_id NOT IN "
            "(SELECT id FROM programs)"
        )).scalar_one()
    assert all(v == 0 for v in orphans.values()), f"cascades incomplete: {orphans}"
    assert n_ms == 0, "milestones not cascaded through programs"


def test_orphan_inserts_rejected_on_migrated_schema(migrated_engine):
    """FK integrity is live on SQLite dev too (WS04-04 parity with Postgres)."""
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        with migrated_engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO attempts (user_id, type, task, prompt, body, bands,"
                " criteria, cefr, metrics, created_at) "
                "VALUES (999999, 'writing', 'task2', '', 'x', '{}', '{}',"
                " 'B2', '{}', CURRENT_TIMESTAMP)"
            ))


# ── WS08-04/05: migration discipline (chain integrity + boot) ────────────────

def _heads() -> list[str]:
    from alembic.script import ScriptDirectory

    sd = ScriptDirectory.from_config(_alembic_config("sqlite://"))
    return sd.get_heads()


def test_migration_chain_has_exactly_one_head():
    """Parallel workstreams must merge revisions — a second head silently
    leaves production databases on a partial chain (WS08-04)."""
    heads = _heads()
    assert len(heads) == 1, f"multiple Alembic heads: {heads}"


def test_downgrade_one_then_reupgrade(migrated_engine):
    """Upgrade from the maintained prior revision succeeds (WS08-04: every
    release must be reachable from production-like prior state)."""
    url = migrated_engine.url.render_as_string(hide_password=False)
    cfg = _alembic_config(url)
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        # The module fixture already sits at head; step back and re-apply.
        command.downgrade(cfg, "-1")
        command.upgrade(cfg, "head")
    finally:
        if old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old
    insp = inspect(migrated_engine)
    assert "attempts" in insp.get_table_names()
    assert "task_exposure" in insp.get_table_names()


def test_app_boots_against_migrated_schema(migrated_engine):
    """WS08-05: the application must start (engine init + seed + health)
    against the migrated schema, not only against metadata."""
    from app import create_app

    url = migrated_engine.url.render_as_string(hide_password=False)
    app = create_app(overrides={"TESTING": True, "DATABASE_URL": url})
    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True


def test_alembic_version_matches_head(migrated_engine):
    """The stamped revision equals the chain head after a full upgrade."""
    with migrated_engine.connect() as conn:
        stamped = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert stamped == _heads()[0]


# ── WS08-05: PostgreSQL migration evidence (CI; skipped locally) ─────────────

PG_URL = os.getenv("TEST_MIGRATIONS_PG_URL")


@pytest.fixture(scope="module")
def pg_engine():
    """Full chain on a real PostgreSQL 18 database (CI migrations job)."""
    os.environ["DATABASE_URL"] = PG_URL
    try:
        command.upgrade(_alembic_config(PG_URL), "head")
        engine = create_engine(PG_URL)
        yield engine
        engine.dispose()
    finally:
        if os.environ.get("DATABASE_URL") == PG_URL:
            os.environ.pop("DATABASE_URL", None)


@pytest.mark.skipif(not PG_URL, reason="TEST_MIGRATIONS_PG_URL not set")
def test_pg_chain_applies_and_boots_app(pg_engine):
    """SQLite-only tests are not sufficient evidence for PostgreSQL migration
    behaviour (08 WS08-05): chain applies on PG and the app boots on it."""
    from app import create_app

    insp = inspect(pg_engine)
    for table in ("attempts", "user_profile", "auth_session", "jobs",
                  "ai_usage_ledger", "analytics_events", "task_exposure"):
        assert table in insp.get_table_names(), f"{table} missing after PG upgrade"

    app = create_app(overrides={"TESTING": True, "DATABASE_URL": PG_URL})
    resp = app.test_client().get("/api/health")
    assert resp.status_code == 200


@pytest.mark.skipif(not PG_URL, reason="TEST_MIGRATIONS_PG_URL not set")
def test_pg_fk_integrity_enforced(pg_engine):
    """PostgreSQL enforces ownership FKs natively (WS04 parity on PG)."""
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with pg_engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO attempts (user_id, type, task, prompt, body, bands,"
                " criteria, cefr, metrics, created_at) "
                "VALUES (999999, 'writing', 'task2', '', 'x', '{}', '{}',"
                " 'B2', '{}', now())"
            ))

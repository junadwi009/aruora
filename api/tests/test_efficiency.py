from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.data.models import Base, TestGate, Feedback, GenUsage
from app.data.repositories import Repository


def test_models_have_expected_columns():
    assert TestGate.__tablename__ == "test_gate"
    assert set(TestGate.__table__.columns.keys()) >= {"user_id", "active_seconds", "unlocked_at"}
    assert Feedback.__tablename__ == "feedback"
    assert set(Feedback.__table__.columns.keys()) >= {"id", "user_id", "stars", "insight", "created_at"}
    assert GenUsage.__tablename__ == "gen_usage"
    assert set(GenUsage.__table__.columns.keys()) >= {"id", "user_id", "day", "count"}


def _repo():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Repository(sessionmaker(bind=eng))


def _repo_with_user():
    """FKs are enforced everywhere now (WS04-04) — helper creates a real user."""
    r = _repo()
    u = r.create_account("eff@example.com", "correct horse battery staple")
    return r, u.id


def test_gate_accumulate_and_unlock():
    r, uid = _repo_with_user()
    assert r.gate_get(uid)["active_seconds"] == 0
    assert r.gate_add_seconds(uid, 60) == 60
    assert r.gate_add_seconds(uid, 60) == 120
    assert r.gate_get(uid)["unlocked_at"] is None
    r.gate_unlock(uid)
    assert r.gate_get(uid)["unlocked_at"] is not None
    r.gate_unlock(uid)  # idempotent, no raise


def test_feedback_add_and_list():
    r, uid = _repo_with_user()
    fid = r.feedback_add(uid, 5, "Really useful for listening drills.")
    assert isinstance(fid, int)
    rows = r.feedback_list()
    assert rows[0]["stars"] == 5 and rows[0]["user_id"] == uid


def test_gen_usage_counter_is_per_day():
    r, uid = _repo_with_user()
    assert r.gen_count_today(uid, "2026-07-25") == 0
    assert r.gen_incr_today(uid, "2026-07-25") == 1
    assert r.gen_incr_today(uid, "2026-07-25") == 2
    assert r.gen_count_today(uid, "2026-07-26") == 0


def test_pool_count_and_add():
    r = _repo()
    assert r.count_sets("reading", "B2") == 0
    r.add_set("reading", "B2", {"passage": "x"})
    assert r.count_sets("reading", "B2") == 1
    assert r.count_sets("reading", "B1") == 0


from app.config import Config
from app.routes._gencap import serve_or_generate


def test_efficiency_config_defaults():
    c = Config({})
    assert c.GATE_ENABLED is True
    assert c.GATE_LOCK_SECONDS == 25200
    assert c.GATE_HEARTBEAT_SEC == 60
    assert c.POOL_TARGET == 7
    assert c.DAILY_GEN_CAP == 20
    assert c.MODEL_SCORE == "deepseek/deepseek-chat-v3.1:free"


def test_efficiency_config_overrides():
    c = Config({"POOL_TARGET": 3, "DAILY_GEN_CAP": 0, "GATE_ENABLED": "0"})
    assert c.POOL_TARGET == 3
    assert c.DAILY_GEN_CAP == 0
    assert c.GATE_ENABLED is False


def _seeded_client(overrides=None):
    from app import create_app
    from app.data.seed import seed_all
    from app.services.llm import LlmGateway
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    repo = Repository(Session)

    class FakeGW:
        calls = 0
        def generate(self, *a, **k):
            FakeGW.calls += 1
            # WS27: content is hashed + deduplicated on insert, so each
            # generated set must be distinct for the pool to actually grow.
            return {"title": f"Generated {FakeGW.calls}",
                    "passage": f"generated {FakeGW.calls}", "questions": []}
    gw = FakeGW()
    cfg = {"TESTING": True, "REPO": repo, "GATEWAY": gw, "POOL_TARGET": 2, "DAILY_GEN_CAP": 3}
    cfg.update(overrides or {})
    app = create_app(cfg)
    c = app.test_client()
    c.post("/api/account/register", json={"email": "g@example.com", "password": "correct horse battery staple"})
    return c, repo, gw

def _gencap_context(overrides=None):
    """Exercise the retained pool/cap subsystem directly.

    ARUORA v1.2 Reading/Listening routes now start server-owned practice
    sessions through practice.start_for(), so route calls are no longer a
    valid proxy for _gencap behaviour.
    """
    repo = _repo()
    user = repo.create_account(
        "gencap@example.com",
        "correct horse battery staple",
    )

    class FakeGW:
        def __init__(self):
            self.calls = 0

        def generate(self, *args, **kwargs):
            self.calls += 1
            return {
                "title": f"Generated {self.calls}",
                "passage": f"generated {self.calls}",
                "questions": [],
            }

    values = {
        "POOL_TARGET": 2,
        "DAILY_GEN_CAP": 3,
        "GATE_ENABLED": "0",
    }
    values.update(overrides or {})

    return repo, user.id, FakeGW(), Config(values)


def test_gencap_generates_until_pool_target_then_serves():
    repo, uid, gw, cfg = _gencap_context()

    serve_or_generate(
        "reading", "B2", uid, repo, cfg, gw,
        {"band": "A2"},
    )
    serve_or_generate(
        "reading", "B2", uid, repo, cfg, gw,
        {"band": "A2"},
    )

    assert repo.count_sets("reading", "A2") == 2
    assert gw.calls == 2

    # Once the pool is full, serve existing content without another LLM call.
    served = serve_or_generate(
        "reading", "B2", uid, repo, cfg, gw,
        {"band": "A2"},
    )

    assert gw.calls == 2
    assert repo.count_sets("reading", "A2") == 2
    assert served["title"] in {"Generated 1", "Generated 2"}


def test_gencap_new_band_reenters_generation():
    repo, uid, gw, cfg = _gencap_context()

    # Explicitly fill B2 so this test only measures band isolation.
    repo.add_set(
        "reading",
        "B2",
        {"title": "Seed 1", "questions": []},
    )
    repo.add_set(
        "reading",
        "B2",
        {"title": "Seed 2", "questions": []},
    )

    serve_or_generate(
        "reading", "B2", uid, repo, cfg, gw,
        {"band": "B2"},
    )

    assert gw.calls == 0

    serve_or_generate(
        "reading", "B2", uid, repo, cfg, gw,
        {"band": "C1"},
    )

    assert gw.calls == 1
    assert repo.count_sets("reading", "C1") == 1


def test_gencap_daily_cap_serves_existing_pool_without_extra_generation():
    repo, uid, gw, cfg = _gencap_context(
        {
            "POOL_TARGET": 99,
            "DAILY_GEN_CAP": 2,
        }
    )

    serve_or_generate(
        "listening", "B1", uid, repo, cfg, gw,
        {"band": "B1"},
    )
    serve_or_generate(
        "listening", "B1", uid, repo, cfg, gw,
        {"band": "B1"},
    )

    assert gw.calls == 2
    assert repo.count_sets("listening", "B1") == 2

    # Daily entitlement is exhausted, but existing pool content remains usable.
    served = serve_or_generate(
        "listening", "B1", uid, repo, cfg, gw,
        {"band": "B1"},
    )

    assert gw.calls == 2
    assert repo.count_sets("listening", "B1") == 2
    assert served["title"] in {"Generated 1", "Generated 2"}

def test_vocab_capped_returns_429():
    c, repo, gw = _seeded_client(overrides={"DAILY_GEN_CAP": 1})
    # vocab route is POST /api/vocab (not /generate); FakeGW.generate returns a dict
    first = c.post("/api/vocab", json={"level": "B1", "topic": "travel"})
    assert first.status_code == 200
    second = c.post("/api/vocab", json={"level": "B1", "topic": "travel"})
    assert second.status_code == 429
    assert second.get_json()["error"]["code"] == "GEN_CAP_REACHED"

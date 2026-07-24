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


def test_gate_accumulate_and_unlock():
    r = _repo()
    assert r.gate_get(1)["active_seconds"] == 0
    assert r.gate_add_seconds(1, 60) == 60
    assert r.gate_add_seconds(1, 60) == 120
    assert r.gate_get(1)["unlocked_at"] is None
    r.gate_unlock(1)
    assert r.gate_get(1)["unlocked_at"] is not None
    r.gate_unlock(1)  # idempotent, no raise


def test_feedback_add_and_list():
    r = _repo()
    fid = r.feedback_add(1, 5, "Really useful for listening drills.")
    assert isinstance(fid, int)
    rows = r.feedback_list()
    assert rows[0]["stars"] == 5 and rows[0]["user_id"] == 1


def test_gen_usage_counter_is_per_day():
    r = _repo()
    assert r.gen_count_today(1, "2026-07-25") == 0
    assert r.gen_incr_today(1, "2026-07-25") == 1
    assert r.gen_incr_today(1, "2026-07-25") == 2
    assert r.gen_count_today(1, "2026-07-26") == 0


def test_pool_count_and_add():
    r = _repo()
    assert r.count_sets("reading", "B2") == 0
    r.add_set("reading", "B2", {"passage": "x"})
    assert r.count_sets("reading", "B2") == 1
    assert r.count_sets("reading", "B1") == 0


from app.config import Config


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
            return {"passage": "generated", "questions": []}
    gw = FakeGW()
    cfg = {"TESTING": True, "REPO": repo, "GATEWAY": gw, "POOL_TARGET": 2, "DAILY_GEN_CAP": 3}
    cfg.update(overrides or {})
    app = create_app(cfg)
    c = app.test_client()
    c.post("/api/account/register", json={"email": "g@example.com", "password": "secret123"})
    return c, repo, gw


def test_reading_generates_until_pool_target_then_serves():
    c, repo, gw = _seeded_client()
    # POOL_TARGET=2. Use band "A2": fixtures/seed_sets.json only seeds "B2"
    # reading sets, so "A2" starts with an empty pool (unlike "B2", which
    # ships with 5 seeded sets and would already be frozen at POOL_TARGET=2).
    # first two calls generate + grow pool
    c.post("/api/reading/generate", json={"band": "A2"})
    c.post("/api/reading/generate", json={"band": "A2"})
    assert repo.count_sets("reading", "A2") == 2
    assert gw.calls == 2
    # third call: pool full -> serve from pool, no new generate
    c.post("/api/reading/generate", json={"band": "A2"})
    assert gw.calls == 2
    assert repo.count_sets("reading", "A2") == 2


def test_new_band_reenters_generation():
    c, repo, gw = _seeded_client()
    c.post("/api/reading/generate", json={"band": "B2"})
    c.post("/api/reading/generate", json={"band": "B2"})  # B2 pool full (target 2)
    before = gw.calls
    c.post("/api/reading/generate", json={"band": "C1"})  # new band -> generates
    assert gw.calls == before + 1
    assert repo.count_sets("reading", "C1") == 1


def test_daily_cap_blocks_further_generation():
    c, repo, gw = _seeded_client(overrides={"POOL_TARGET": 99, "DAILY_GEN_CAP": 2})
    c.post("/api/listening/generate", json={"band": "B1"})
    c.post("/api/listening/generate", json={"band": "B1"})
    # cap=2 reached; pool has 2 sets -> fall back to serve, status 200, no generate
    r = c.post("/api/listening/generate", json={"band": "B1"})
    assert r.status_code == 200
    assert gw.calls == 2

"""WS07-02/08 — cost accounting ledger, concurrency limit, provider budget,
and the hard kill-switch (paid AI halts; account/export/delete stay up).
"""

import fakeredis
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.costguard import AI_HALTED_FLAG, ConcurrencyLimiter
from app.data.models import AiUsageLedger, Base
from app.data.repositories import Repository
from app.kv import MemoryKV
from app.services.llm import LlmGateway

STAFF_PW = "correct horse battery staple"


def _repo() -> Repository:
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Repository(sessionmaker(bind=eng))


@pytest.fixture()
def app_client():
    repo = _repo()
    app = create_app({
        "TESTING": True,
        "REPO": repo,
        "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
        "KV": MemoryKV(),
    })
    c = app.test_client()
    c.post("/api/account/register",
           json={"email": "cost@example.com", "password": STAFF_PW})
    return c, repo, app


def _ledger_rows(repo):
    with repo.session_factory() as s:
        return s.query(AiUsageLedger).all()


# ── usage ledger (WS07-08) ────────────────────────────────────────────────────

def test_scoring_records_an_append_only_ledger_row(app_client):
    c, repo, app = app_client
    r = c.post("/api/writing/evaluate",
               json={"taskType": "task2", "prompt": "p", "essay": "Some learner text."})
    assert r.status_code == 200
    rows = _ledger_rows(repo)
    assert len(rows) == 1
    row = rows[0]
    assert row.cost_center == "learner_scoring"
    assert row.op == "score"
    assert row.skill == "writing"
    assert row.status == "ok"
    assert row.provider == "stub" and row.model_requested == "stub"
    # No learner content ever lands in the ledger.
    blob = str(row.__dict__)
    assert "Some learner text" not in blob


def test_failed_scoring_is_accounted_not_fabricated(app_client):
    c, repo, app = app_client

    class Down:
        def score(self, *a, **k):
            from app.errors import ApiError
            raise ApiError("LLM_UNAVAILABLE", "LLM call failed: Timeout", 502)

    app.config["GATEWAY"] = Down()
    r = c.post("/api/writing/evaluate",
               json={"taskType": "task2", "prompt": "p", "essay": "text"})
    assert r.status_code == 502
    rows = _ledger_rows(repo)
    assert len(rows) == 1
    assert rows[0].status == "failed"
    assert rows[0].error_code == "LLM_UNAVAILABLE"


# ── provider budget + kill-switch (WS07-08) ──────────────────────────────────

def test_admin_halt_blocks_paid_ai_but_not_account_flows(app_client):
    c, repo, app = app_client
    repo.flag_set(AI_HALTED_FLAG, "1")
    r = c.post("/api/writing/evaluate",
               json={"taskType": "task2", "prompt": "p", "essay": "text"})
    assert r.status_code == 503
    assert r.get_json()["error"]["code"] == "AI_BUDGET_HALTED"
    # The halt must NOT take account functionality down (WS07 required test).
    assert c.get("/api/account/export").status_code == 200
    assert c.get("/api/account/me").status_code == 200
    assert c.delete("/api/account").status_code == 200


def test_env_kill_switch_fails_closed(app_client):
    c, repo, app = app_client
    # Simulate the env-only emergency switch.
    app.config["APP_CONFIG"].AI_BUDGET_KILL = True
    r = c.post("/api/writing/evaluate",
               json={"taskType": "task2", "prompt": "p", "essay": "text"})
    assert r.status_code == 503
    assert r.get_json()["error"]["code"] == "AI_BUDGET_HALTED"
    # …and it cannot be cleared via the admin flag.
    repo.flag_set(AI_HALTED_FLAG, "")
    assert c.post("/api/writing/evaluate",
                  json={"taskType": "task2", "prompt": "p", "essay": "text"}
                  ).status_code == 503


def test_daily_budget_ceiling_auto_halts(app_client):
    c, repo, app = app_client
    uid = c.get("/api/account/me").get_json()["id"]
    repo.ledger_add(cost_center="learner_scoring", op="score",
                    user_id=uid, cost_micros=5_000_000,
                    cost_source="provider_reported")
    app.config["APP_CONFIG"].AI_DAILY_BUDGET_MICROS = 1_000_000
    r = c.post("/api/writing/evaluate",
               json={"taskType": "task2", "prompt": "p", "essay": "text"})
    assert r.status_code == 503
    assert r.get_json()["error"]["code"] == "AI_BUDGET_HALTED"


def test_budget_ledger_survives_account_deletion(app_client):
    """Ledger user_id is ON DELETE SET NULL: the financial record outlives the
    account but loses its personal identifier (no learner content inside)."""
    c, repo, app = app_client
    c.post("/api/writing/evaluate",
           json={"taskType": "task2", "prompt": "p", "essay": "text"})
    assert len(_ledger_rows(repo)) == 1
    c.delete("/api/account")
    rows = _ledger_rows(repo)
    assert len(rows) == 1 and rows[0].user_id is None


# ── concurrency limit (WS07-02) ──────────────────────────────────────────────

def test_concurrency_slots_are_per_user_and_release_correctly():
    conc = ConcurrencyLimiter(redis_client=fakeredis.FakeRedis(decode_responses=True))
    assert conc.acquire("score:u:1", limit=1, ttl_sec=60)
    assert not conc.acquire("score:u:1", limit=1, ttl_sec=60)
    assert conc.acquire("score:u:2", limit=1, ttl_sec=60)  # User B unaffected
    conc.release("score:u:1")
    assert conc.acquire("score:u:1", limit=1, ttl_sec=60)
    conc.release("score:u:1")
    conc.release("score:u:1")  # never goes negative / corrupts the slot
    conc.release("score:u:1")
    conc.release("score:u:1")
    assert conc.acquire("score:u:1", limit=1, ttl_sec=60)


def test_concurrency_limit_rejects_with_429(app_client):
    from app.errors import ApiError
    conc = ConcurrencyLimiter()
    with pytest.raises(ApiError) as err:
        with conc.slot("score:u:9", limit=1, ttl_sec=60):
            with conc.slot("score:u:9", limit=1, ttl_sec=60):
                pass
    assert err.value.code == "CONCURRENCY_LIMIT" and err.value.status == 429


# ── admin budget surface ─────────────────────────────────────────────────────

def test_admin_budget_endpoints():
    repo = _repo()
    app = create_app({
        "TESTING": True,
        "REPO": repo,
        "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
        "KV": MemoryKV(),
        "ADMIN_EMAILS": "boss@example.com",
    })
    admin = app.test_client()
    anon = app.test_client()
    admin.post("/api/account/register",
               json={"email": "boss@example.com", "password": STAFF_PW})
    anon.post("/api/account/register",
              json={"email": "pleb@example.com", "password": STAFF_PW})

    # Non-admins are locked out of the budget surface.
    assert anon.get("/api/admin/ai-budget").status_code == 403

    body = admin.get("/api/admin/ai-budget").get_json()
    assert body["halted"] is False and body["killSwitchEnv"] is False

    assert admin.post("/api/admin/ai-budget", json={"halt": True}).status_code == 200
    body = admin.get("/api/admin/ai-budget").get_json()
    assert body["halted"] is True and body["adminHalt"] is True

    assert admin.post("/api/admin/ai-budget", json={"halt": False}).status_code == 200
    assert admin.get("/api/admin/ai-budget").get_json()["halted"] is False

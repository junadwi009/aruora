"""WS07-03/04/05/06/07 — job records, idempotency, queue split, retry policy,
backpressure, retention, and user-scoped status lookup.
"""

import fakeredis
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.errors import ApiError
from app.jobs import handlers
from app.jobs.service import JobService, canonical_payload_hash
from app.kv import MemoryKV
from app.services.llm import LlmGateway


def _repo() -> Repository:
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Repository(sessionmaker(bind=eng))


def _cfg(**over) -> Config:
    return Config({"QUEUE_MAX_DEPTH": "2", "JOB_RETENTION_HOURS": "24", **over})


@pytest.fixture()
def dispatched():
    return []


@pytest.fixture()
def jobs(dispatched):
    repo = _repo()
    svc = JobService(repo, _cfg(), dispatcher=lambda *a: dispatched.append(a))
    return svc, repo, dispatched


def _uid(repo, email: str) -> int:
    """Real profile id — FKs are enforced everywhere (WS04-04)."""
    return repo.create_account(email, STAFF_PW).id


STAFF_PW = "correct horse battery staple"


# ── idempotency (WS07-05) ─────────────────────────────────────────────────────

def test_duplicate_key_same_payload_returns_existing_job(jobs):
    svc, repo, dispatched = jobs
    uid = _uid(repo, "alice@example.com")
    a, created_a = svc.enqueue("score_writing", queue="llm_score",
                               payload={"essay": "same"}, user_id=uid,
                               idempotency_key="k1")
    b, created_b = svc.enqueue("score_writing", queue="llm_score",
                               payload={"essay": "same"}, user_id=uid,
                               idempotency_key="k1")
    assert created_a and not created_b
    assert a["id"] == b["id"]
    assert len(dispatched) == 1  # the provider is called at most once


def test_same_key_different_payload_is_rejected(jobs):
    svc, repo, dispatched = jobs
    uid = _uid(repo, "alice@example.com")
    svc.enqueue("score_writing", queue="llm_score", payload={"essay": "one"},
                user_id=uid, idempotency_key="k1")
    with pytest.raises(ApiError) as err:
        svc.enqueue("score_writing", queue="llm_score", payload={"essay": "two"},
                    user_id=uid, idempotency_key="k1")
    assert err.value.code == "IDEMPOTENCY_CONFLICT"
    assert err.value.status == 409


def test_idempotency_keys_are_per_user(jobs):
    svc, repo, dispatched = jobs
    uid1 = _uid(repo, "alice@example.com")
    uid2 = _uid(repo, "bob@example.com")
    a, _ = svc.enqueue("score_writing", queue="llm_score", payload={"x": 1},
                       user_id=uid1, idempotency_key="shared")
    b, created = svc.enqueue("score_writing", queue="llm_score", payload={"x": 1},
                             user_id=uid2, idempotency_key="shared")
    assert created and a["id"] != b["id"]


def test_payload_hash_is_canonical(jobs):
    assert canonical_payload_hash({"a": 1, "b": 2}) == canonical_payload_hash({"b": 2, "a": 1})
    assert canonical_payload_hash({"a": 1}) != canonical_payload_hash({"a": 2})


# ── backpressure (WS07-07) ────────────────────────────────────────────────────

def test_saturated_queue_rejects_with_retryable_error():
    svc = JobService(_repo(), _cfg(), dispatcher=lambda *a: None,
                     redis_client=fakeredis.FakeRedis(decode_responses=True))
    r = svc._redis
    r.rpush("llm_score", "j1")
    r.rpush("llm_score", "j2")  # QUEUE_MAX_DEPTH=2 reached
    with pytest.raises(ApiError) as err:
        svc.enqueue("score_writing", queue="llm_score", payload={}, user_id=None)
    assert err.value.code == "BACKPRESSURE" and err.value.status == 503


def test_unreachable_depth_probe_fails_closed():
    """A broker that cannot report depth counts as saturated — never enqueue
    blind while protecting the wallet."""
    class _Deaf:
        def llen(self, *_):
            raise ConnectionError("broker down")

    svc = JobService(_repo(), _cfg(QUEUE_MAX_DEPTH="1"),
                     dispatcher=lambda *a: None, redis_client=_Deaf())
    with pytest.raises(ApiError) as err:
        svc.enqueue("score_writing", queue="llm_score", payload={}, user_id=None)
    assert err.value.code == "BACKPRESSURE"


# ── user-scoped status + retention (WS07-03/05) ──────────────────────────────

def test_user_cannot_read_another_users_job():
    repo = _repo()
    app = create_app({"TESTING": True, "REPO": repo,
                      "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
                      "KV": MemoryKV()})
    svc = app.config["JOBS"]
    a = app.test_client()
    b = app.test_client()
    a.post("/api/account/register",
           json={"email": "alice@example.com", "password": STAFF_PW})
    b.post("/api/account/register",
           json={"email": "bob@example.com", "password": STAFF_PW})
    ida = a.get("/api/account/me").get_json()["id"]
    job, _ = svc.enqueue("score_writing", queue="llm_score", payload={"x": 1},
                         user_id=ida)

    assert a.get(f"/api/jobs/{job['id']}").status_code == 200
    # B cannot read (or even confirm) A's job; sequential guessing is equally 404.
    assert b.get(f"/api/jobs/{job['id']}").status_code == 404
    assert b.get("/api/jobs/00000000-0000-0000-0000-000000000000").status_code == 404
    # Unauthenticated requests see nothing.
    anon = app.test_client()
    assert anon.get(f"/api/jobs/{job['id']}").status_code == 401


def test_expired_jobs_hide_results_and_report_expired(jobs):
    svc, repo, dispatched = jobs
    uid = _uid(repo, "carol@example.com")
    job, _ = svc.enqueue("score_writing", queue="llm_score", payload={"x": 1},
                         user_id=uid)
    repo.job_set_succeeded(job["id"], {"bands": {"overall": 6.5}})
    # Force the retention window into the past.
    with repo.session_factory() as s:
        from app.data.models import Job
        j = s.get(Job, job["id"])
        from datetime import datetime, timedelta, timezone
        j.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        s.commit()

    out = svc.get_status(job["id"], uid)
    assert out["status"] == "expired"
    assert "result" not in out


# ── retry policy + safe errors (WS07-06) ─────────────────────────────────────

class FlakyGateway:
    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def generate(self, *a, **k):
        self.calls += 1
        if self.calls <= self.failures:
            raise ApiError("LLM_UNAVAILABLE", "LLM call failed: Timeout", 502)
        return {"passage": "ok", "questions": [], "_meta_llm": {
            "provider": "stub", "requestedModel": "stub", "resolvedModel": None,
            "latencyMs": 1, "promptTokens": None, "completionTokens": None,
            "cachedTokens": None, "reasoningTokens": None, "costUsd": None,
        }}


def _ctx(repo, cfg, gw):
    return {"repo": repo, "cfg": cfg, "gateway": gw}


def test_transient_llm_errors_are_retried_then_succeed():
    repo = _repo()
    cfg = _cfg(REPLENISH_DAILY_BUDGET="10", POOL_TARGET="7")
    gw = FlakyGateway(failures=2)
    job = repo.job_create("11111111-1111-1111-1111-111111111111", "replenish_pool",
                          "llm_generate", {"skill": "reading", "band": "B2"},
                          "hash")
    handlers.execute_job(job["id"], _ctx(repo, cfg, gw), sleep=lambda a: None)
    done = repo.job_get(job["id"])
    assert done["status"] == "succeeded"
    assert gw.calls == 3  # 2 transient failures + 1 success
    assert repo.count_sets("reading", "B2") == 1


def test_invalid_model_output_is_never_retried():
    repo = _repo()
    cfg = _cfg()
    gw = FlakyGateway(failures=0)

    def bad_output(payload, ctx):
        raise ApiError("LLM_BAD_OUTPUT", "model did not return valid JSON", 502)

    handlers.HANDLERS["replenish_pool"] = bad_output
    try:
        job = repo.job_create("22222222-2222-2222-2222-222222222222",
                              "replenish_pool", "llm_generate",
                              {"skill": "reading", "band": "B2"}, "h")
        handlers.execute_job(job["id"], _ctx(repo, cfg, gw), sleep=lambda a: None)
        assert repo.job_get(job["id"])["status"] == "failed"
    finally:
        handlers.HANDLERS["replenish_pool"] = handlers.replenish_pool


def test_failed_job_leaks_no_provider_detail():
    repo = _repo()
    cfg = _cfg()

    def exploding(payload, ctx):
        raise RuntimeError("OPENROUTER_API_KEY=sk-secret stack trace here")

    handlers.HANDLERS["replenish_pool"] = exploding
    try:
        job = repo.job_create("33333333-3333-3333-3333-333333333333",
                              "replenish_pool", "llm_generate",
                              {"skill": "reading", "band": "B2"}, "h")
        handlers.execute_job(job["id"], _ctx(repo, cfg, None), sleep=lambda a: None)
        done = repo.job_get(job["id"])
        assert done["status"] == "failed"
        assert done["errorCode"] == "INTERNAL_JOB_ERROR"
        blob = str(done)
        assert "sk-secret" not in blob and "OPENROUTER" not in blob
    finally:
        handlers.HANDLERS["replenish_pool"] = handlers.replenish_pool


def test_retryable_classification():
    assert handlers.is_retryable("replenish_pool", "LLM_UNAVAILABLE", 0)
    assert not handlers.is_retryable("replenish_pool", "LLM_UNAVAILABLE", 3)
    assert not handlers.is_retryable("replenish_pool", "LLM_BAD_OUTPUT", 0)
    assert not handlers.is_retryable("replenish_pool", "VALIDATION", 0)
    # Unknown job types default to no retry.
    assert not handlers.is_retryable("future_type", "LLM_UNAVAILABLE", 0)


# ── shared-pool replenishment (WS07-10 migration rule) ───────────────────────

def test_replenish_is_a_system_cost_center_not_learner_entitlement():
    repo = _repo()
    cfg = _cfg(REPLENISH_DAILY_BUDGET="10", POOL_TARGET="7")
    gw = FlakyGateway(failures=0)
    job = repo.job_create("44444444-4444-4444-4444-444444444444", "replenish_pool",
                          "llm_generate", {"skill": "reading", "band": "B2"}, "h")
    handlers.execute_job(job["id"], _ctx(repo, cfg, gw), sleep=lambda a: None)
    assert repo.count_sets("reading", "B2") == 1
    # The ledger records the system cost centre — no GenUsage row was touched.
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    assert repo.ledger_count_ops(start, now + timedelta(seconds=1), "pool_replenish") == 1
    with repo.session_factory() as s:
        from app.data.models import GenUsage
        assert s.query(GenUsage).count() == 0


def test_replenish_budget_exhaustion_cancels_the_job():
    repo = _repo()
    cfg = _cfg(REPLENISH_DAILY_BUDGET="0", POOL_TARGET="7")
    gw = FlakyGateway(failures=0)
    job = repo.job_create("55555555-5555-5555-5555-555555555555", "replenish_pool",
                          "llm_generate", {"skill": "reading", "band": "B2"}, "h")
    handlers.execute_job(job["id"], _ctx(repo, cfg, gw), sleep=lambda a: None)
    done = repo.job_get(job["id"])
    assert done["status"] == "cancelled"
    assert done["errorCode"] == "REPLENISH_BUDGET_EXHAUSTED"
    assert gw.calls == 0


def test_replenish_at_pool_target_is_a_noop():
    repo = _repo()
    cfg = _cfg(POOL_TARGET="1")
    gw = FlakyGateway(failures=0)
    repo.add_set("reading", "B2", {"passage": "seeded"})
    job = repo.job_create("66666666-6666-6666-6666-666666666666", "replenish_pool",
                          "llm_generate", {"skill": "reading", "band": "B2"}, "h")
    handlers.execute_job(job["id"], _ctx(repo, cfg, gw), sleep=lambda a: None)
    done = repo.job_get(job["id"])
    assert done["status"] == "succeeded"
    assert gw.calls == 0


# ── queued-mode route flow: replenishment replaces inline generation ─────────

@pytest.fixture()
def queued_app():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    repo = Repository(Session)  # no seeds: every pool starts empty
    gw = FlakyGateway(failures=0)

    class MetaGW:
        """FlakyGateway + stub-like metadata for the ledger."""
        def generate(self, *a, **k):
            out = gw.generate(*a, **k)
            out["_meta_llm"] = {
                "provider": "stub", "requestedModel": "stub",
                "resolvedModel": None, "latencyMs": 1,
                "promptTokens": None, "completionTokens": None,
                "cachedTokens": None, "reasoningTokens": None, "costUsd": None,
            }
            return out

    app = create_app({
        "TESTING": True,
        "REPO": repo,
        "GATEWAY": MetaGW(),
        "KV": MemoryKV(),
        "REDIS_URL": "redis://faketarget/0",  # → queued topology
        "REDIS": fakeredis.FakeRedis(decode_responses=True),
        "JOBS_DISPATCH": "eager",             # …with inline execution for tests
        "POOL_TARGET": "2",
    })
    client = app.test_client()
    client.post("/api/account/register",
                json={"email": "queen@example.com", "password": STAFF_PW})
    return client, repo, gw, app


def test_empty_pool_enqueues_replenishment_instead_of_inline_generation(queued_app):
    client, repo, gw, app = queued_app
    # No seeds exist in this fixture: every pool starts empty, so queued mode
    # must NOT generate synchronously for the learner request.
    r = client.post("/api/reading/generate", json={"band": "A2"})
    assert r.status_code == 503
    assert r.get_json()["error"]["code"] == "POOL_EMPTY"
    # The provider call that DID happen (eager dispatcher) belongs to the
    # system replenishment job — the learner request path stayed inference-free.
    assert gw.calls == 1

    # …and exactly ONE idempotent system job exists for the bucket/epoch.
    with repo.session_factory() as s:
        from app.data.models import Job
        rows = s.query(Job).filter(Job.type == "replenish_pool").all()
    assert len(rows) == 1
    assert rows[0].status == "succeeded"
    assert ":sys:" in rows[0].idempotency_key  # system cost centre, no user
    assert repo.count_sets("reading", "A2") == 1

    # A learner entitlement was never decremented for pool content (WS07-10).
    from app.routes._gencap import today_utc
    assert repo.gen_count_today(
        client.get("/api/account/me").get_json()["id"], today_utc()) == 0

    # The next request is a normal free pool serve — no additional provider work.
    r2 = client.post("/api/reading/generate", json={"band": "A2"})
    assert r2.status_code == 200
    assert gw.calls == 1


def test_queue_overload_does_not_break_login_profile_history(queued_app):
    client, repo, gw, app = queued_app
    # Saturate the replenishment queue.
    fake = app.config["JOBS"]._redis
    for i in range(100):  # >= QUEUE_MAX_DEPTH default
        fake.rpush("llm_generate", f"stale{i}")
    # …so a fresh empty-pool request fails gracefully without enqueueing…
    r = client.post("/api/reading/generate", json={"band": "A2"})
    assert r.status_code == 503  # POOL_EMPTY (backpressure is swallowed upstream)
    # …while ordinary account/history endpoints stay fully functional.
    assert client.get("/api/account/me").status_code == 200
    assert client.get("/api/history/attempts").status_code == 200
    other = app.test_client()
    assert other.post("/api/account/register",
                      json={"email": "zulu@example.com",
                            "password": STAFF_PW}
                      ).status_code in (200, 400)  # 400 only if already exists

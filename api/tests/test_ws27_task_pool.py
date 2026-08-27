"""WS27 — Task Pool economy: lifecycle, anti-repeat selection, dedup,
accounting separation, entitlement policy, and scraping/integrity controls.

Doc: docs/production-readiness/27 §29 (required tests) / §30 (release gates).
Stage A accounting primitives were landed with WS07; these tests cover the
Stage B/C/E deltas: validated Task Bank, per-user exposure, pool-first serving.
"""

import fakeredis
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import AiUsageLedger, Base, GeneratedSet, TaskExposure
from app.data.repositories import Repository
from app.jobs import handlers
from app.kv import MemoryKV
from app.services import task_pool
from app.services.llm import LlmGateway

PW = "correct horse battery staple"


def _repo(*seeded) -> Repository:
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    repo = Repository(sessionmaker(bind=eng))
    for payload in seeded:
        repo.add_set("reading", "B2", payload, source="seed")
    return repo


def _cfg(**over) -> Config:
    base = {"POOL_TARGET": "7", "REPLENISH_DAILY_BUDGET": "10",
            "POOL_REPEAT_COOLDOWN_HOURS": "24"}
    base.update(over)
    return Config(base)


def _set(i: int) -> dict:
    return {"title": f"T{i}", "passage": f"passage {i}",
            "questions": [{"stem": f"q{i}?", "options": ["a", "b"],
                           "answer": "a", "explanation": "e"}]}


# ── selection: anti-repeat + exposure (27 §9) ────────────────────────────────

def test_unseen_item_preferred_over_seen():
    repo = _repo(_set(1), _set(2))
    cfg = _cfg()
    uid = repo.create_account("u1@example.com", PW).id
    first = task_pool.serve_next("reading", "B2", uid, repo, cfg)
    second = task_pool.serve_next("reading", "B2", uid, repo, cfg)
    assert first and second
    # With two unseen items, the second serve cannot repeat the first.
    assert second["payload"] != first["payload"]
    assert second["repeat"] is False


def test_cooldown_deprioritises_but_exhausted_pool_degrades_visibly():
    repo = _repo(_set(1))
    cfg = _cfg()
    uid = repo.create_account("u1@example.com", PW).id
    first = task_pool.serve_next("reading", "B2", uid, repo, cfg)
    second = task_pool.serve_next("reading", "B2", uid, repo, cfg)
    assert first["payload"] == second["payload"]
    assert second["repeat"] is True  # measurable repeat, never a silent illusion
    with repo.session_factory() as s:
        assert s.query(TaskExposure).count() == 2


def test_backdated_exposure_outside_cooldown_is_serveable():
    from datetime import datetime, timedelta, timezone
    repo = _repo(_set(1))
    cfg = _cfg()
    uid = repo.create_account("u1@example.com", PW).id
    with repo.session_factory() as s:
        s.add(TaskExposure(user_id=uid, set_id=1, served_at=datetime.now(timezone.utc) - timedelta(hours=48)))
        s.commit()
    out = task_pool.serve_next("reading", "B2", uid, repo, cfg)
    assert out is not None and out["repeat"] is True


def test_quarantined_and_retired_inventory_never_served():
    repo = _repo(_set(1), _set(2))
    cfg = _cfg()
    uid = repo.create_account("u1@example.com", PW).id
    repo.quarantine_set(1, ["schema:bad"])
    repo.retire_set(2)
    assert task_pool.serve_next("reading", "B2", uid, repo, cfg) is None
    # …and quarantined rows don't count toward the replenishment threshold.
    assert repo.count_active_sets("reading", "B2") == 0


def test_adjacent_band_fallback_records_actual_difficulty():
    repo = _repo()
    repo.add_set("reading", "B1", _set(9), source="seed")
    cfg = _cfg()
    uid = repo.create_account("u1@example.com", PW).id
    out = task_pool.serve_next("reading", "B2", uid, repo, cfg)
    assert out is not None
    assert out["servedFrom"]["band"] == "B1"
    assert out["context"] == "fallback_adjacent"


def test_selection_never_crosses_skill():
    repo = _repo()
    repo.add_set("listening", "B2", _set(9), source="seed")
    uid = repo.create_account("u1@example.com", PW).id
    assert task_pool.serve_next("reading", "B2", uid, repo, _cfg()) is None


def test_served_response_exposes_no_internal_metadata():
    repo = _repo(_set(1))
    uid = repo.create_account("u1@example.com", PW).id
    out = task_pool.serve_next("reading", "B2", uid, repo, _cfg())
    blob = str(out["payload"]) + str(out)
    for secret in ("status", "content_hash", "generation_meta", "gen_cost",
                   "quality_flags", "serve_count"):
        assert secret not in blob.lower().replace("servedfrom", "").replace("repeat", "")


# ── lifecycle: validation before activation (27 §13) ─────────────────────────

def test_validation_rejects_answer_key_inconsistency():
    bad = _set(1)
    bad["questions"][0]["options"] = ["x", "y"]  # answer "a" not among options
    ok, flags = task_pool.validate_candidate("reading", "B2", bad)
    assert not ok and any("answer_key" in f for f in flags)


def test_validation_accepts_a_well_formed_set():
    ok, flags = task_pool.validate_candidate("reading", "B2", _set(1))
    assert ok and flags == []


# ── replenishment pipeline (27 §29) ──────────────────────────────────────────

class ScriptedGateway:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = 0

    def generate(self, *a, **k):
        self.calls += 1
        p = self.payloads.pop(0)
        if isinstance(p, Exception):
            raise p
        return {**p, "_meta_llm": {"provider": "stub", "requestedModel": "stub",
                                   "resolvedModel": None, "latencyMs": 1,
                                   "promptTokens": None, "completionTokens": None,
                                   "cachedTokens": None, "reasoningTokens": None,
                                   "costUsd": None}}


def _ctx(repo, cfg, gw):
    return {"repo": repo, "cfg": cfg, "gateway": gw}


def _job(repo, jid="77777777-7777-7777-7777-777777777777"):
    return repo.job_create(jid, "replenish_pool", "llm_generate",
                           {"skill": "reading", "band": "B2"}, "h")


def test_validation_failure_does_not_activate_task():
    repo = _repo()
    bad = _set(1)
    bad["questions"][0]["answer"] = "zzz"  # not among options
    gw = ScriptedGateway([bad])
    job = _job(repo)
    handlers.execute_job(job["id"], _ctx(repo, _cfg(), gw), sleep=lambda a: None)
    done = repo.job_get(job["id"])
    assert done["status"] == "succeeded"  # the JOB ran fine…
    assert done["result"]["status"] == "rejected"
    # …but the bank only holds the QUARANTINED audit copy, never servable.
    assert repo.count_active_sets("reading", "B2") == 0
    with repo.session_factory() as s:
        row = s.get(GeneratedSet, s.query(GeneratedSet.id).first()[0])
        assert row.status == "quarantined" and row.quality_flags["flags"]


def test_rejected_generation_is_counted_in_cost_accounting():
    repo = _repo()
    bad = _set(1)
    bad["questions"][0]["answer"] = "zzz"
    gw = ScriptedGateway([bad])
    job = _job(repo)
    handlers.execute_job(job["id"], _ctx(repo, _cfg(), gw), sleep=lambda a: None)
    with repo.session_factory() as s:
        rows = s.query(AiUsageLedger).all()
    assert len(rows) == 1 and rows[0].status == "rejected"
    assert rows[0].error_code == "LLM_BAD_OUTPUT"


def test_exact_duplicate_never_enters_active_pool():
    repo = _repo()
    gw = ScriptedGateway([_set(1), _set(1)])  # identical content twice
    for jid in ("88888888-8888-8888-8888-888888888888",
                "99999999-9999-9999-9999-999999999999"):
        job = _job(repo, jid)
        handlers.execute_job(job["id"], _ctx(repo, _cfg(), gw), sleep=lambda a: None)
    assert repo.count_active_sets("reading", "B2") == 1
    with repo.session_factory() as s:
        led = s.query(AiUsageLedger).order_by(AiUsageLedger.id).all()
    assert [r.status for r in led] == ["ok", "rejected"]
    assert led[1].error_code == "DUPLICATE"


def test_activated_task_carries_provenance_and_cost():
    repo = _repo()
    payload = _set(1)
    gw = ScriptedGateway([payload])
    job = _job(repo)
    handlers.execute_job(job["id"], _ctx(repo, _cfg(), gw), sleep=lambda a: None)
    with repo.session_factory() as s:
        row = s.query(GeneratedSet).filter_by(status="active").one()
        assert row.content_hash
        assert row.generation_meta.get("provider") == "stub"
        assert row.activated_at is not None


# ── pool-first serving: pool serves never create billable usage ──────────────

@pytest.fixture()
def queued_app():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    repo = Repository(sessionmaker(bind=eng))  # no seeds: pools start empty
    gw = ScriptedGateway([_set(i) for i in range(10)])
    app = create_app({
        "TESTING": True,
        "REPO": repo,
        "GATEWAY": gw,
        "KV": MemoryKV(),
        "REDIS_URL": "redis://faketarget/0",
        "REDIS": fakeredis.FakeRedis(decode_responses=True),
        "JOBS_DISPATCH": "eager",
        "POOL_TARGET": "5",
    })
    c = app.test_client()
    c.post("/api/account/register", json={"email": "pool@example.com", "password": PW})
    return c, repo, gw, app


def test_try_another_consumes_pool_not_provider_calls(queued_app):
    c, repo, gw, app = queued_app
    r1 = c.post("/api/reading/generate", json={"band": "A2"})
    assert r1.status_code == 503  # bootstrap: replenishment enqueued (eager)…
    assert gw.calls == 1          # …one SYSTEM generation, not the request path
    r2 = c.post("/api/reading/generate", json={"band": "A2"})
    assert r2.status_code == 200
    calls_after_first_serve = gw.calls
    # "Try another": repeated serves consume pooled inventory, never the LLM.
    for _ in range(3):
        rr = c.post("/api/reading/generate", json={"band": "A2"})
        assert rr.status_code == 200
    assert gw.calls == calls_after_first_serve
    with repo.session_factory() as s:
        assert s.query(AiUsageLedger).filter(
            AiUsageLedger.cost_center == "learner_scoring").count() == 0


def test_pool_serve_records_exposure_and_repeat_metric(queued_app):
    c, repo, gw, app = queued_app
    c.post("/api/reading/generate", json={"band": "A2"})  # 503 → replenish
    uid = c.get("/api/account/me").get_json()["id"]
    # Fill the bucket: 1 replenished + 4 inserted = 5 active items.
    for i in range(100, 104):
        repo.add_set("reading", "A2", _set(i), source="seed")
    for _ in range(7):
        r = c.post("/api/reading/generate", json={"band": "A2"})
        assert r.status_code == 200
    with repo.session_factory() as s:
        exposures = s.query(TaskExposure).filter_by(user_id=uid).all()
    assert len(exposures) == 7
    # 7 serves over 5 items → exactly two cooldown-window repeats, recorded.
    assert sum(1 for e in exposures if e.repeat) == 2


def test_pool_endpoints_cannot_dump_inventory(queued_app):
    c, repo, gw, app = queued_app
    for i in range(200, 205):
        repo.add_set("reading", "A2", _set(i), source="seed")
    r = c.post("/api/reading/generate", json={"band": "A2"})
    body = r.get_data(as_text=True)
    # Exactly ONE task per request — never a list, never the whole bucket.
    assert body.count('"title"') == 1 and body.count('"passage"') == 1
    import json as _json
    assert isinstance(_json.loads(body), dict)


def test_client_cannot_spoof_usage_metadata(queued_app):
    c, repo, gw, app = queued_app
    app.config["GATEWAY"] = LlmGateway(Config({"LLM_MODE": "stub"}))
    r = c.post("/api/writing/evaluate", json={
        "taskType": "task2", "prompt": "p", "essay": "learner text.",
        "promptTokens": 1, "completionTokens": 1, "costUsd": 0.0,
        "_meta_llm": {"provider": "fake", "costUsd": 999},
    })
    assert r.status_code == 200
    with repo.session_factory() as s:
        rows = s.query(AiUsageLedger).filter_by(cost_center="learner_scoring").all()
    assert len(rows) == 1
    assert rows[0].provider == "stub"      # server-side gateway metadata
    assert rows[0].cost_micros is None     # client-supplied "costUsd" ignored


# ── entitlement policy service (27 §7/§26 Stage E) ───────────────────────────

def test_custom_generation_entitlement_is_per_user():
    from app.services.ai_usage import custom_generation_allowed, note_custom_generation, require_custom_generation
    repo = _repo()
    cfg = _cfg(DAILY_GEN_CAP="1")
    a = repo.create_account("ent1@example.com", PW).id
    b = repo.create_account("ent2@example.com", PW).id
    assert custom_generation_allowed(a, repo, cfg)
    note_custom_generation(a, repo)
    assert not custom_generation_allowed(a, repo, cfg)
    with pytest.raises(Exception) as err:
        require_custom_generation(a, repo, cfg)
    assert err.value.code == "GEN_CAP_REACHED"
    assert custom_generation_allowed(b, repo, cfg)  # B unaffected


def test_usage_summary_derives_from_ledger_only():
    from app.services.ai_usage import usage_summary
    repo = _repo()
    repo.ledger_add(cost_center="learner_scoring", op="score",
                    cost_micros=1500, cost_source="provider_reported")
    summary = usage_summary(repo)
    assert summary["ops"]["learner_scoring"] == 1
    assert summary["ops"]["pool_serves"] == 0  # pool serves are ledger-free
    assert summary["costMicros"] == 1500

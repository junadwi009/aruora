"""Queue acceptance, ownership, outbox recovery and fail-closed execution.

Provider calls use stub fixtures; these tests never send mail or paid inference.
The separate broker canary proves delivery over real Redis/PostgreSQL.
"""
from datetime import timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app import create_app
from app.config import Config
from app.data.models import Base, Attempt, Job, JobDispatch
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.jobs.service import JobService
from app.jobs.handlers import execute_job
from app.jobs.delivery import claim_job, dispatch_one, recover_pending, fail_uncertain_running, utcnow
from app.services.llm import LlmGateway

PASSWORD = "correct horse battery staple"
BODY = {"part": "part2", "question": "Describe a skill you learned.",
        "transcript": "I learned to write programs by practising every day and reviewing mistakes with my friends."}


@pytest.fixture
def system():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    sf = sessionmaker(bind=eng)
    seed_all(sf)
    repo = Repository(sf)
    calls = []
    gw = LlmGateway(Config({"LLM_MODE": "stub"}))
    counted = Mock(wraps=gw)
    app = create_app({"TESTING": True, "REPO": repo, "GATEWAY": counted,
                      "JOBS_DISPATCH": lambda *args: calls.append(args)})
    client = app.test_client()
    user = client.post("/api/account/register", json={"email": "queued@example.com", "password": PASSWORD}).json
    cfg = app.config["APP_CONFIG"]
    cfg.REDIS_URL = "redis://not-contacted:6379/0"
    jobs = app.config["JOBS"]
    jobs.mode = "queued"
    yield app, client, repo, jobs, counted, calls, user["id"]
    eng.dispose()


def submit(system, key="test-reference-0001", body=None):
    return system[1].post("/api/speaking/evaluate", json=body or BODY,
                          headers={"Idempotency-Key": key})


def test_receipt_is_immediate_and_provider_runs_only_in_handler(system):
    app, client, repo, jobs, gw, calls, uid = system
    response = submit(system)
    assert response.status_code == 202
    jid = response.json["jobId"]
    gw.score.assert_not_called()
    assert len(calls) == 1
    assert calls[0][0] == jid and calls[0][2] == {}  # no essay/audio in broker arguments
    assert repo.job_get(jid)["status"] == "queued"
    execute_job(jid, jobs._ctx())
    status = client.get(f"/api/jobs/{jid}").json
    assert status["status"] == "succeeded"
    assert status["result"]["savedId"]
    assert status["result"]["estimateScope"] == "speaking_text_estimate"
    assert "userId" not in status and "payload" not in status
    assert repo.job_get(jid)["payload"] == {}
    assert gw.score.call_count == 1
    assert not repo.session_factory().query(JobDispatch).count()


def test_same_key_recovers_same_result_no_second_inference(system):
    _, client, repo, jobs, gw, _, uid = system
    jid = submit(system).json["jobId"]
    execute_job(jid, jobs._ctx())
    first = jobs.get_status(jid, uid)["result"]["savedId"]
    assert submit(system).json["jobId"] == jid
    execute_job(jid, jobs._ctx())  # broker redelivery after ACK loss
    assert gw.score.call_count == 1
    assert jobs.get_status(jid, uid)["result"]["savedId"] == first
    lookup = client.get("/api/jobs/lookup?type=score_speaking&key=test-reference-0001")
    assert lookup.status_code == 200 and lookup.json["id"] == jid


def test_same_key_changed_body_conflicts(system):
    submit(system)
    changed = {**BODY, "transcript": BODY["transcript"] + " A different response."}
    r = submit(system, body=changed)
    assert r.status_code == 409 and r.json["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_production_scoring_requires_bounded_key(system):
    r = system[1].post("/api/speaking/evaluate", json=BODY)
    assert r.status_code == 422
    assert submit(system, "x" * 65).status_code == 422
    system[4].score.assert_not_called()


def test_bounded_pending_work_still_allows_same_key_recovery(system):
    assert submit(system, "request-0001").status_code == 202
    assert submit(system, "request-0002").status_code == 202
    assert submit(system, "request-0003").status_code == 429
    assert submit(system, "request-0001").status_code == 202


def test_owner_isolation_lookup_export_and_deletion(system):
    app, first, repo, jobs, gw, _, uid = system
    jid = submit(system).json["jobId"]
    other = app.test_client()
    other.post("/api/account/register", json={"email": "other@example.com", "password": PASSWORD})
    assert other.get(f"/api/jobs/{jid}").status_code == 404
    assert other.get("/api/jobs/lookup?type=score_speaking&key=test-reference-0001").status_code == 404
    assert other.get("/api/account/export").json["pendingEvaluations"] == []
    pending = first.get("/api/account/export").json["pendingEvaluations"]
    assert len(pending) == 1 and pending[0]["input"]["transcript"] == BODY["transcript"]
    first.delete("/api/account")
    execute_job(jid, jobs._ctx())
    gw.score.assert_not_called()
    with repo.session_factory() as s:
        assert s.get(Job, jid) is None and s.get(JobDispatch, jid) is None


def test_kill_switch_checked_at_execution_not_only_enqueue(system):
    app, _, repo, jobs, gw, _, _ = system
    jid = submit(system).json["jobId"]
    app.config["APP_CONFIG"].AI_BUDGET_KILL = True
    execute_job(jid, jobs._ctx())
    assert repo.job_get(jid)["errorCode"] == "AI_BUDGET_HALTED"
    gw.score.assert_not_called()


def test_email_ownership_rechecked_in_worker(system):
    app, _, repo, jobs, gw, _, _ = system
    jid = submit(system).json["jobId"]
    app.config["APP_CONFIG"].EMAIL_VERIFICATION_REQUIRED = True
    execute_job(jid, jobs._ctx())
    assert repo.job_get(jid)["errorCode"] == "EMAIL_UNVERIFIED"
    gw.score.assert_not_called()


def test_publish_failure_retains_intent_and_recovers_same_job(system):
    _, _, repo, jobs, gw, _, _ = system
    jobs._dispatch = Mock(side_effect=ConnectionError("synthetic broker outage"))
    response = submit(system)
    assert response.status_code == 202  # accepted durably, not fabricated success
    jid = response.json["jobId"]
    published = []
    assert recover_pending(repo, lambda *a: published.append(a), now=utcnow()+timedelta(seconds=31)) == 1
    assert len(published) == 1 and published[0][0] == jid
    execute_job(jid, jobs._ctx())
    execute_job(jid, jobs._ctx())
    assert gw.score.call_count == 1


def test_atomic_claim_and_outbox_removal(system):
    _, _, repo, _, _, _, _ = system
    jid = submit(system).json["jobId"]
    assert claim_job(repo, jid) is True
    assert claim_job(repo, jid) is False
    with repo.session_factory() as s:
        assert s.get(JobDispatch, jid) is None
        assert s.get(Job, jid).attempts == 1


def test_expired_queued_job_never_runs(system):
    _, _, repo, jobs, gw, _, _ = system
    jid = submit(system).json["jobId"]
    with repo.session_factory() as s:
        j = s.get(Job, jid); j.expires_at = utcnow()-timedelta(seconds=1); s.commit()
    execute_job(jid, jobs._ctx())
    assert not dispatch_one(repo, jid, Mock())
    assert repo.job_get(jid)["status"] == "expired"
    gw.score.assert_not_called()


def test_uncertain_running_work_is_not_automatically_replayed(system):
    _, _, repo, jobs, gw, _, _ = system
    jid = submit(system).json["jobId"]
    assert claim_job(repo, jid)
    assert fail_uncertain_running(repo, now=utcnow()+timedelta(seconds=901)) == 1
    execute_job(jid, jobs._ctx())
    assert repo.job_get(jid)["errorCode"] == "JOB_OUTCOME_UNCERTAIN"
    gw.score.assert_not_called()


def test_late_bookkeeping_error_cannot_downgrade_saved_result(system):
    _, _, repo, jobs, _, _, _ = system
    jid = submit(system).json["jobId"]
    execute_job(jid, jobs._ctx())
    before = repo.job_get(jid)["result"]
    repo.job_fail(jid, "LATE_ERROR", "Must not overwrite committed success")
    repo.job_cancel(jid, "LATE_CANCEL", "Must not overwrite committed success")
    assert repo.job_get(jid)["status"] == "succeeded"
    assert repo.job_get(jid)["result"] == before


def test_failure_to_persist_result_rolls_back_attempt(system, monkeypatch):
    from app.services.evaluation import persist_result
    from app.schemas import SpeakingEvaluateIn
    from sqlalchemy import event
    _, _, repo, _, _, _, uid = system
    jid = submit(system).json["jobId"]
    assert claim_job(repo, jid)
    def deny_commit(session):
        raise RuntimeError("synthetic commit failure")
    event.listen(repo.session_factory, "before_commit", deny_commit)
    try:
        with pytest.raises(RuntimeError):
            persist_result(repo, uid, "speaking", SpeakingEvaluateIn(**BODY), {"bands":{},"cefr":"B1"}, jid)
    finally:
        event.remove(repo.session_factory, "before_commit", deny_commit)
    with repo.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id==uid)) == 0
        assert s.get(Job, jid).status == "running"


def test_writing_queue_retains_metrics_and_single_saved_attempt(system):
    _, client, repo, jobs, gw, _, _ = system
    body = {"taskType":"task2", "prompt":"Should transport be free?", "essay":"Public transport helps people reach school and work. It should be reliable and affordable for everyone."}
    r = client.post("/api/writing/evaluate", json=body, headers={"Idempotency-Key":"writing-reference-0001"})
    assert r.status_code == 202
    jid = r.json["jobId"]
    gw.score.assert_not_called()
    execute_job(jid, jobs._ctx())
    result = repo.job_get(jid)["result"]
    assert result["metrics"]["wordCount"] == len(body["essay"].split())
    assert result["savedId"]
    assert gw.score.call_args.args[0] == "writing"
    assert gw.score.call_args.kwargs["essay"] == body["essay"]


def test_outbox_migration_backfills_only_queued_and_downgrades(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config as AlembicConfig
    from sqlalchemy import inspect, text
    from pathlib import Path
    url = "sqlite:///" + str(tmp_path/"migration.db")
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = AlembicConfig(str(Path(__file__).resolve().parents[1]/"alembic.ini"))
    command.upgrade(cfg, "a12c20260929")
    engine = create_engine(url)
    with engine.begin() as conn:
        for status in ("queued","running","succeeded"):
            conn.execute(text("INSERT INTO jobs (id,type,queue,status,payload,payload_hash,created_at,attempts) VALUES (:id,'test','llm_score',:status,'{}','hash',CURRENT_TIMESTAMP,0)"), {"id":status,"status":status})
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert list(conn.execute(text("SELECT job_id FROM job_dispatch")).scalars()) == ["queued"]
    command.downgrade(cfg, "a12c20260929")
    assert "job_dispatch" not in inspect(engine).get_table_names()
    command.upgrade(cfg, "head")
    engine.dispose()


@pytest.mark.parametrize("secret", ["", "   "])
def test_blank_session_secret_rejected(secret):
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        create_app({"SESSION_SECRET":secret})


def test_guarded_gateway_stops_all_inference_entrypoints(system):
    from app.errors import ApiError
    app, _, _, _, raw, _, _ = system
    gateway = app.config["GATEWAY"]
    app.config["APP_CONFIG"].AI_BUDGET_KILL = True
    for name in ("score","generate"):
        with pytest.raises(ApiError) as exc:
            getattr(gateway,name)("roleplay")
        assert exc.value.code == "AI_BUDGET_HALTED"
    raw.score.assert_not_called(); raw.generate.assert_not_called()

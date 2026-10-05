"""Real Redis -> Celery process -> PostgreSQL -> authenticated API canary.

Opt-in CI only. Every account/response is synthetic and the provider is stub.
This is NOT a deployment/TLS/real-provider acceptance test.
"""
import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

PG = os.getenv("TEST_JOBS_PG_URL")
REDIS = os.getenv("TEST_JOBS_REDIS_URL")
pytestmark = pytest.mark.skipif(not (PG and REDIS), reason="isolated PostgreSQL/Redis canary not configured")


def test_real_broker_delivery_redelivery_recovery_and_atomic_claim(tmp_path):
    from app import create_app
    from app.config import Config
    from app.data.models import Attempt, Job, JobDispatch
    from app.data.repositories import Repository
    from app.data.seed import seed_all
    from app.jobs.delivery import claim_job, utcnow, recover_pending
    from app.jobs.celery_app import make_celery
    from app.services.llm import LlmGateway
    from datetime import timedelta

    engine = create_engine(PG, pool_pre_ping=True)
    sf = sessionmaker(bind=engine)
    seed_all(sf)
    repo = Repository(sf)
    app = create_app({"TESTING": True, "REPO": repo, "GATEWAY": LlmGateway(Config({"LLM_MODE":"stub"})),
                      "REDIS_URL": REDIS, "EMAIL_VERIFICATION_REQUIRED": False})
    client = app.test_client()
    uid = client.post("/api/account/register", json={"email": f"canary-{uuid.uuid4().hex}@example.com",
                       "password":"correct horse battery staple"}).json["id"]
    jobs = app.config["JOBS"]
    key = str(uuid.uuid4())
    body = {"part":"part2", "question":"Describe a skill.",
            "transcript":"I learned to read carefully and check my answers before moving to the next question."}
    # Accept before a consumer exists: API response must not wait for inference.
    started = time.monotonic()
    response = client.post("/api/speaking/evaluate", json=body, headers={"Idempotency-Key": key})
    assert response.status_code == 202, response.json
    assert time.monotonic() - started < 5
    jid = response.json["jobId"]
    assert repo.job_get(jid)["status"] == "queued"
    assert client.get("/api/account/me").status_code == 200
    assert client.get("/api/health/ready").status_code == 200
    env = {**os.environ, "DATABASE_URL":PG, "REDIS_URL":REDIS, "LLM_MODE":"stub",
           "APP_ENV":"development", "EMAIL_VERIFICATION_REQUIRED":"0",
           "FAIL_CLOSED_ON_MAIL":"0", "AI_BUDGET_KILL":"0", "ASR_ENABLED":"0"}
    log_path = tmp_path / "worker.log"
    with log_path.open("w+") as log:
        process = subprocess.Popen([sys.executable, "-m", "celery", "-A", "app.jobs.celery_app:celery",
            "worker", "-Q", "llm_score,maintenance", "--pool=solo", "--concurrency=1", "--loglevel=warning"],
            cwd=Path(__file__).resolve().parents[1], env=env, stdout=log, stderr=subprocess.STDOUT)
        def await_success(job_id):
            limit = time.monotonic()+45
            while time.monotonic() < limit:
                state = repo.job_get(job_id)
                if state["status"] in ("failed","cancelled","expired"):
                    pytest.fail(f"Canary failed: {state['errorCode']}")
                if state["status"] == "succeeded":
                    return state
                if process.poll() is not None:
                    log.flush();pytest.fail("Celery process exited: " + log_path.read_text()[-3000:])
                time.sleep(.2)
            log.flush();pytest.fail("Canary timed out: " + log_path.read_text()[-3000:])
        try:
            done = await_success(jid)
            saved = done["result"]["savedId"]
            assert saved
            assert client.get(f"/api/jobs/{jid}").json["result"]["savedId"] == saved
            assert client.post("/api/speaking/evaluate", json=body,
                               headers={"Idempotency-Key":key}).json["jobId"] == jid
            make_celery(REDIS).send_task("app.jobs.run_job", args=[jid], queue="llm_score")
            # Broker publication interrupted after DB commit. Real recovery uses
            # the normal dispatcher and the same job rather than a new request.
            original = jobs._dispatch
            def unavailable(*args):
                raise ConnectionError("synthetic interrupted publish")
            jobs._dispatch = unavailable
            second = client.post("/api/speaking/evaluate", json=body,
                                 headers={"Idempotency-Key":str(uuid.uuid4())}).json["jobId"]
            jobs._dispatch = original
            with sf() as s:
                row = s.get(JobDispatch,second);row.not_before=utcnow()-timedelta(seconds=1);s.commit()
            # Use the actual maintenance task on its separate queue, not direct
            # handler execution. Beat's schedule is checked by unit contracts.
            make_celery(REDIS).send_task("app.jobs.recover_delivery", queue="maintenance")
            await_success(second)
            with sf() as s:
                assert s.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id==uid)) == 2
            # Competing worker claims on PostgreSQL: exactly one CAS may win.
            claim_id = str(uuid.uuid4())
            repo.job_create(claim_id, "score_speaking", "llm_score", {}, "test", user_id=uid)
            with ThreadPoolExecutor(max_workers=8) as pool:
                assert sum(pool.map(lambda _: claim_job(repo,claim_id), range(8))) == 1
            repo.job_fail(claim_id,"CANARY_FINISHED","Synthetic concurrency check completed")
            # Late duplicate delivery cannot downgrade a committed result.
            assert repo.job_get(jid)["result"]["savedId"] == saved
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=5)
            repo.delete_account(uid)
            engine.dispose()

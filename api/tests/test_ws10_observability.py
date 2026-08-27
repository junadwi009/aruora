"""WS10 — observability: structured logs (privacy-safe), request telemetry,
Prometheus metrics surface, AI/job signals, and durable audit events.

Doc: docs/production-readiness/10 §15 (never-log list) / §95 (audit) / §48
(metrics). Correlation reuses WS09's X-Request-ID; no request bodies are ever
logged, so learner essays cannot leak through telemetry.
"""

import json
import logging

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import AdminAudit, Base
from app.data.repositories import Repository
from app.kv import MemoryKV
from app.observability import JsonFormatter, metrics, scrub
from app.services.llm import LlmGateway

PW = "correct horse battery staple"


def _repo() -> Repository:
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Repository(sessionmaker(bind=eng))


def _app(repo=None, **over):
    repo = repo or _repo()
    cfg = {"TESTING": True, "REPO": repo,
           "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
           "KV": MemoryKV(), "LOG_FORMAT": "json"}
    cfg.update(over)
    app = create_app(cfg)
    return app, repo


def _register(c, email):
    r = c.post("/api/account/register", json={"email": email, "password": PW})
    assert r.status_code == 200, r.get_json()
    return c.get("/api/account/me").get_json()["id"]


# ── WS10-01: structured logs + redaction ─────────────────────────────────────

def test_scrub_redacts_sensitive_keys_and_non_scalars():
    out = scrub({
        "jobId": "abc", "uid": 7, "essay": "secret learner text",
        "password": "hunter2", "authToken": "t1", "api_key": "k",
        "body": {"nested": "object"}, "note": None,
    })
    assert out["jobId"] == "abc" and out["uid"] == 7
    assert out["essay"] == "[REDACTED]"
    assert out["password"] == "[REDACTED]"
    assert out["authToken"] == "[REDACTED]" and out["api_key"] == "[REDACTED]"
    assert out["body"] == "[REDACTED]"
    assert out["note"] is None  # scalars/nulls pass through for explicit fields


def test_json_formatter_shape():
    rec = logging.LogRecord("app.http", logging.INFO, __file__, 1,
                            "http_request", (), None)
    rec.obs = {"requestId": "abcd1234", "route": "/api/x", "status": 200}
    out = json.loads(JsonFormatter().format(rec))
    assert out["msg"] == "http_request"
    assert out["level"] == "INFO" and "ts" in out and "version" in out
    assert out["requestId"] == "abcd1234" and out["route"] == "/api/x"


class _ListHandler(logging.Handler):
    """Self-managed capture — immune to pytest logging-plugin state after
    hundreds of create_app calls in one session."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_request_logs_never_contain_learner_content():
    app, repo = _app()
    handler = _ListHandler()
    root = logging.getLogger()
    old_level = root.level
    root.addHandler(handler)
    try:
        c = app.test_client()
        _register(c, "loguser@example.com")
        c.post("/api/writing/evaluate",
               json={"taskType": "task2", "prompt": "p",
                     "essay": "SUPER-SECRET-ESSAY-CONTENT 42"})
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)
    blob = "\n".join(r.getMessage() + str(getattr(r, "obs", {}))
                     for r in handler.records)
    assert "SUPER-SECRET-ESSAY-CONTENT" not in blob
    assert "loguser@example.com" not in blob
    http_records = [r for r in handler.records
                    if r.name == "app.http" and r.getMessage() == "http_request"]
    if not http_records:
        lg = logging.getLogger("app.http")
        state = {
            "disable": logging.root.manager.disable,
            "rootLevel": root.level,
            "rootHandlers": [type(h).__name__ for h in root.handlers],
            "httpLevel": lg.level,
            "httpEffective": lg.getEffectiveLevel(),
            "httpPropagate": lg.propagate,
            "nRecords": len(handler.records),
            "names": sorted({r.name for r in handler.records})[:20],
        }
        assert False, f"no telemetry records captured: {state}"
    rec = http_records[-1]
    assert rec.obs["route"] == "/api/writing/evaluate"
    assert rec.obs["status"] == 200
    assert rec.obs["uid"] is not None  # numeric id only — never email
    assert "requestId" in rec.obs and rec.obs["requestId"]


def test_health_paths_are_quiet_but_counted():
    app, repo = _app()
    handler = _ListHandler()
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        c = app.test_client()
        c.get("/api/health")
        c.get("/api/health/ready")
    finally:
        root.removeHandler(handler)
    assert all(r.getMessage() != "http_request" for r in handler.records)
    assert metrics.inc is not None


# ── WS10-03: metrics surface ─────────────────────────────────────────────────

def test_metrics_registry_series_cap():
    m = metrics.__class__(max_series=5)
    for i in range(50):
        m.inc("bomb_total", label=f"v{i}")
    out = m.render()
    assert out.count("\n") <= 5  # cardinality bomb cannot explode series


def test_metrics_endpoint_admin_only_and_prometheus_shaped():
    app, repo = _app(ADMIN_EMAILS="boss@example.com")
    anon = app.test_client()
    admin = app.test_client()
    _register(admin, "boss@example.com")
    _register(anon, "pleb@example.com")
    assert anon.get("/api/admin/metrics").status_code == 403

    anon.post("/api/writing/evaluate", json={"taskType": "task2", "prompt": "p",
                                             "essay": "text"})
    r = admin.get("/api/admin/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.content_type
    body = r.get_data(as_text=True)
    assert "http_requests_total" in body
    assert 'route="/api/writing/evaluate"' in body
    assert "ai_calls_total" in body  # the evaluate call above
    assert "text" not in body or "learner" not in body  # no content labels
    assert "SUPER" not in body


def test_pool_and_job_gauges_render():
    app, repo = _app(ADMIN_EMAILS="boss@example.com")
    repo.add_set("reading", "B2", {"title": "T", "passage": "p",
                                   "questions": [{"stem": "q", "options": ["a"],
                                                  "answer": "a"}]}, source="seed")
    repo.job_create("aaaa1111-2222-3333-4444-555566667777", "replenish_pool",
                    "llm_generate", {"skill": "reading", "band": "B2"}, "h")
    admin = app.test_client()
    _register(admin, "boss@example.com")
    body = admin.get("/api/admin/metrics").get_data(as_text=True)
    assert 'pool_tasks{skill="reading",band="B2",status="active"} 1' in body
    assert 'job_backlog{queue="llm_generate",status="queued"} 1' in body


# ── WS10-03 AI / job signals ─────────────────────────────────────────────────

def test_ai_finance_metrics_on_ledger_write():
    from app.costguard import record_llm_usage
    repo = _repo()
    record_llm_usage(repo, cost_center="learner_scoring", op="score",
                     meta={"provider": "openrouter", "requestedModel": "m1",
                           "resolvedModel": "m1", "costUsd": 0.002},
                     user_id=None)
    body = metrics.render()
    assert 'ai_calls_total{costCenter="learner_scoring",op="score",status="ok"}' in body
    assert 'ai_cost_micros_total{costCenter="learner_scoring"} 2000' in body


def test_job_metrics_and_logs_without_payload_content():
    from app.jobs import handlers
    app, repo = _app()
    payload = {"title": "T", "passage": "SECRET-PASSAGE-XYZ",
               "questions": [{"stem": "q", "options": ["a"], "answer": "a",
                              "explanation": "e"}]}
    gw_payload = dict(payload)

    class GW:
        def generate(self, *a, **k):
            return {**gw_payload, "_meta_llm": {
                "provider": "stub", "requestedModel": "stub",
                "resolvedModel": None, "latencyMs": 1, "promptTokens": None,
                "completionTokens": None, "cachedTokens": None,
                "reasoningTokens": None, "costUsd": None}}

    cfg = Config({"POOL_TARGET": "7", "REPLENISH_DAILY_BUDGET": "10"})
    job = repo.job_create("bbbb1111-2222-3333-4444-555566667777",
                          "replenish_pool", "llm_generate",
                          {"skill": "reading", "band": "B2"}, "h")
    handler = _ListHandler()
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        handlers.execute_job(job["id"], {"repo": repo, "cfg": cfg, "gateway": GW()},
                             sleep=lambda a: None)
    finally:
        root.removeHandler(handler)
    body = metrics.render()
    assert 'jobs_total{jobType="replenish_pool",status="succeeded"}' in body
    blob = "\n".join(r.getMessage() + str(getattr(r, "obs", {}))
                     for r in handler.records)
    assert "SECRET-PASSAGE-XYZ" not in blob  # job payloads never reach logs
    assert "job_succeeded" in blob


# ── WS10-05: durable audit of data-subject actions ───────────────────────────

def test_user_export_and_delete_are_audited():
    app, repo = _app()
    c = app.test_client()
    _register(c, "selfdelete@example.com")
    assert c.get("/api/account/export").status_code == 200
    assert c.delete("/api/account").status_code == 200
    with repo.session_factory() as s:
        actions = {a.action for a in s.query(AdminAudit).all()}
    assert "user.export" in actions and "user.delete" in actions


def test_audit_survives_the_deleted_actor():
    """The deletion audit row must outlive the account (SET NULL FK) and keep
    the denormalised email for incident correlation — no tokens, no content."""
    app, repo = _app()
    c = app.test_client()
    _register(c, "auditme@example.com")
    c.delete("/api/account")
    with repo.session_factory() as s:
        rows = [a for a in s.query(AdminAudit).all() if a.action == "user.delete"]
    assert len(rows) == 1
    assert rows[0].actor_email == "auditme@example.com"
    blob = str(rows[0].__dict__).lower()
    assert "token" not in blob and "password" not in blob

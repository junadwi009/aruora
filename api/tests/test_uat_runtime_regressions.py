"""Regressions for readiness and the exact Celery CLI/publisher bootstrap.

These tests never contact a paid provider or require a running broker.
Real publisher-to-worker delivery is a separate staging acceptance check.
"""
import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import Flask

from app.routes.health import bp


def health_client(redis_url="redis://redis:6379/0", repo=None):
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        APP_CONFIG=SimpleNamespace(REDIS_URL=redis_url),
        REPO=repo if repo is not None else SimpleNamespace(),
    )
    app.register_blueprint(bp)
    return app.test_client()


def test_readiness_calls_the_real_redis_module(monkeypatch):
    redis = Mock()
    redis.ping.return_value = True
    build = Mock(return_value=redis)
    monkeypatch.setattr("app.ratelimit.build_redis_client", build)
    result = health_client().get("/api/health/ready")
    assert result.status_code == 200
    assert result.json == {"ok": True, "checks": {"db": True, "redis": True}}
    build.assert_called_once_with("redis://redis:6379/0")
    redis.ping.assert_called_once_with()


@pytest.mark.parametrize("failure", [False, ConnectionError("private broker failure")])
def test_readiness_still_fails_closed(monkeypatch, failure):
    redis = Mock()
    if isinstance(failure, Exception):
        redis.ping.side_effect = failure
    else:
        redis.ping.return_value = failure
    monkeypatch.setattr("app.ratelimit.build_redis_client", Mock(return_value=redis))
    result = health_client().get("/api/health/ready")
    assert result.status_code == 503
    assert result.json == {"ok": False, "checks": {"db": True, "redis": False}}
    assert "private" not in result.get_data(as_text=True)


def test_readiness_does_not_require_optional_redis(monkeypatch):
    build = Mock(side_effect=AssertionError("must not connect"))
    monkeypatch.setattr("app.ratelimit.build_redis_client", build)
    assert health_client(redis_url="").get("/api/health/ready").status_code == 200
    build.assert_not_called()


def test_db_failure_is_not_hidden_by_healthy_redis(monkeypatch):
    redis = Mock()
    redis.ping.return_value = True
    monkeypatch.setattr("app.ratelimit.build_redis_client", Mock(return_value=redis))
    repo = SimpleNamespace(session_factory=Mock(side_effect=RuntimeError("private DB")))
    result = health_client(repo=repo).get("/api/health/ready")
    assert result.status_code == 503
    assert result.json["checks"] == {"db": False, "redis": True}


def test_publisher_preserves_broker_and_cache_isolation():
    from app.jobs.celery_app import make_celery
    one = make_celery("redis://unit-test-one:6379/0")
    two = make_celery("redis://unit-test-two:6379/1")
    assert one.conf.broker_url == "redis://unit-test-one:6379/0"
    assert two.conf.broker_url == "redis://unit-test-two:6379/1"
    assert one is make_celery("redis://unit-test-one:6379/0")
    assert one is not two
    assert set(q.name for q in one.conf.task_queues) == {"asr", "mail", "llm_score", "llm_generate", "maintenance"}
    with pytest.raises(ValueError):
        make_celery("")


def test_cli_worker_and_beat_use_environment_broker():
    env = {**os.environ, "APP_ENV": "production", "REDIS_URL": "redis://cli-contract:6379/2"}
    code = "from app.jobs.celery_app import celery; assert celery.conf.broker_url == 'redis://cli-contract:6379/2'; assert 'ws08-data-lifecycle-maintenance' in celery.conf.beat_schedule"
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_production_worker_refuses_an_implicit_broker():
    env = {**os.environ, "APP_ENV": "production", "REDIS_URL": ""}
    result = subprocess.run([sys.executable, "-c", "from app.jobs.celery_app import celery"], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "Production Celery requires REDIS_URL" in result.stderr

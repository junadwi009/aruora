"""WS10 — observability core: structured logs, request telemetry, metrics.

Design rules (docs/production-readiness/10):

* Logs are structured JSON in production (LOG_FORMAT=json). Fields: ts,
  level, logger, msg, requestId (WS09's X-Request-ID correlation), route
  template, method, status, durationMs, uid (numeric id, never email),
  jobId, errorCode, deployment version.
* NEVER logged: passwords, tokens, session ids, cookies, API keys, DB URLs,
  raw essays/transcripts/audio, full request bodies, sensitive PII. Call
  sites pass fields through :func:`scrub`, which strips anything whose key
  looks sensitive and drops non-scalar values (no accidental body dumps).
* Metrics are an in-process registry exposed in Prometheus text format at
  the admin-only ``/api/admin/metrics`` endpoint. Cardinality is capped and
  labels use bounded values only (route template, status class, error code,
  cost centre, model from config) so a hostile client cannot explode series.
* Distributed tracing (WS10-02, OpenTelemetry) and external error
  aggregation (WS10-04) are deployment add-ons: the correlation id and
  structured fields here are the hooks they attach to. Alerts/runbooks are
  documented for WS15 staging rehearsal (WS10-06/07) — this module supplies
  the observable signals, not the paging infrastructure.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

DEPLOY_VERSION = os.getenv("DEPLOY_VERSION", "dev")

# Any field key containing one of these fragments is REDACTED from logs.
_REDACT_FRAGMENTS = (
    "password", "token", "secret", "api_key", "apikey", "cookie",
    "authorization", "session", "essay", "transcript", "audio", "body",
    "answer", "email",
)


def scrub(fields: dict) -> dict:
    """Keep only plain scalar safe fields; redact sensitive keys. Deny-list
    on keys + type filter on values — belt and braces against content leaks."""
    safe = {}
    for k, v in (fields or {}).items():
        key = str(k).lower()
        if any(f in key for f in _REDACT_FRAGMENTS):
            safe[str(k)] = "[REDACTED]"
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            safe[str(k)] = v if not isinstance(v, str) else v[:500]
    return safe


class JsonFormatter(logging.Formatter):
    """Structured JSON lines — one record, one object, no multi-line stacks
    embedded (exception class only; tracebacks go to error aggregation)."""

    def format(self, record: logging.LogRecord) -> str:
        out = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "version": DEPLOY_VERSION,
        }
        obs = getattr(record, "obs", None)
        if isinstance(obs, dict):
            out.update(scrub(obs))
        if record.exc_info:
            out["exc"] = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
        return json.dumps(out, ensure_ascii=False)


def configure_logging(cfg) -> None:
    """Idempotent logging setup. LOG_FORMAT=json in production compose;
    text keeps local dev readable. LOG_LEVEL default INFO."""
    level = getattr(logging, str(getattr(cfg, "LOG_LEVEL", "INFO") or "INFO").upper(), logging.INFO)
    root = logging.getLogger()
    already = any(getattr(h, "_aruora_ws10", False) for h in root.handlers)
    if already:
        root.setLevel(min(root.level, level))
        return
    handler = logging.StreamHandler()
    handler._aruora_ws10 = True
    if str(getattr(cfg, "LOG_FORMAT", "text")).lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)


# ── metrics registry (in-process; scraped from each API worker) ──────────────

_DEFAULT_BUCKETS = (0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_MAX_SERIES = 500  # cardinality bomb guard


class Metrics:
    def __init__(self, buckets=_DEFAULT_BUCKETS, max_series=_MAX_SERIES) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple, float] = {}
        self._hist: dict[tuple, dict] = {}
        self._buckets = buckets
        self._max = max_series

    def _key(self, name: str, labels: dict) -> tuple:
        return (name, tuple(sorted((str(k), str(v)) for k, v in labels.items())))

    def inc(self, name: str, value: float = 1.0, **labels) -> None:
        with self._lock:
            if len(self._counters) < self._max or self._key(name, labels) in self._counters:
                self._counters[self._key(name, labels)] = \
                    self._counters.get(self._key(name, labels), 0.0) + value

    def observe(self, name: str, value: float, **labels) -> None:
        with self._lock:
            key = self._key(name, labels)
            if key not in self._hist and len(self._hist) >= self._max:
                return
            h = self._hist.setdefault(key, {"sum": 0.0, "count": 0,
                                            "buckets": [0] * len(self._buckets)})
            h["sum"] += value
            h["count"] += 1
            for i, b in enumerate(self._buckets):
                if value <= b:
                    h["buckets"][i] += 1

    def render(self) -> str:
        """Prometheus text exposition (v0.0.4): counters + cumulative hist."""
        lines = []
        with self._lock:
            counters = sorted(self._counters.items())
            hists = sorted(self._hist.items())
        for (name, labels), v in counters:
            lines.append(f"{name}{{{self._fmt(labels)}}} {v}")
        for (name, labels), h in hists:
            base = self._fmt(labels)
            cumulative = 0
            for i, b in enumerate(self._buckets):
                cumulative = h["buckets"][i]  # stored cumulative-by-construction
                lines.append(f'{name}_bucket{{{base},le="{b}"}} {cumulative}')
            lines.append(f'{name}_bucket{{{base},le="+Inf"}} {h["count"]}')
            lines.append(f'{name}_sum{{{base}}} {h["sum"]}')
            lines.append(f'{name}_count{{{base}}} {h["count"]}')
        return "\n".join(lines) + ("\n" if lines else "")

    @staticmethod
    def _fmt(labels) -> str:
        parts = [f'{k}="{v}"' for k, v in labels]
        return ",".join(parts)


metrics = Metrics()

# ── request telemetry ─────────────────────────────────────────────────────────

_QUIET_PATHS = {"/api/health", "/api/health/ready"}


def init_observability(app, cfg) -> None:
    """Attach request telemetry. Consumes WS09's request-id correlation;
    never touches request bodies or response payloads."""
    configure_logging(cfg)
    log = logging.getLogger("app.http")

    @app.before_request
    def _obs_start():
        from flask import g
        g._obs_started = time.perf_counter()
        return None

    @app.after_request
    def _obs_finish(resp):
        from flask import g, request
        duration = time.perf_counter() - getattr(g, "_obs_started",
                                                 time.perf_counter())
        route = request.url_rule.rule if request.url_rule is not None else "unmatched"
        status_class = f"{resp.status_code // 100}xx"
        metrics.inc("http_requests_total", route=route, method=request.method,
                    status=status_class)
        metrics.observe("http_request_duration_seconds", duration,
                        route=route, method=request.method)
        if request.path not in _QUIET_PATHS:
            from .session import current_uid
            from .errors import request_id
            log.info("http_request", extra={"obs": {
                "requestId": request_id(),
                "method": request.method,
                "route": route,
                "status": resp.status_code,
                "durationMs": round(duration * 1000, 1),
                "uid": current_uid(),
            }})
        return resp


def log_op(logger_name: str, level: int, msg: str, **fields) -> None:
    """Structured operational log for non-request paths (jobs, AI ops)."""
    logging.getLogger(logger_name).log(level, msg, extra={"obs": scrub(fields)})

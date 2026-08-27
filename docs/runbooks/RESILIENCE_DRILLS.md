# Runbook — Resilience Drills (TV-08, staging only)

Execute on the staging deployment (production-like compose topology), never
against production data. Each drill: run the drill, record the observed
behaviour + recovery in the log at the bottom, and file any gap. A drill that
has never failed anything has never tested anything — deliberately break the
environment and watch.

## DR-1 — Stop one API replica

```bash
docker compose -f docker-compose.prod.yml pause api && sleep 30 && \
docker compose -f docker-compose.prod.yml unpause api
```

Expect: nginx/proxy serves the static app unchanged; in-flight requests
drain or fail with clean JSON errors (no stack traces); recovery without
manual intervention.

## DR-2 — Restart a worker mid-job

```bash
# submit a writing job, then within its processing window:
docker compose -f docker-compose.prod.yml restart worker-llm
```

Expect: job re-delivered (`acks_late`), `requeue_stale_jobs` flips the stuck
`running` row back to `queued`, job completes exactly once (idempotency key
dedupe); no partial score persisted (WS07-06 retry policy).

## DR-3 — Deny the LLM provider

```bash
# block egress to the provider from the api/worker containers (staging netns)
# or point OPENROUTER_BASE_URL at a blackhole for one run, then:
docker compose -f docker-compose.prod.yml restart api worker-llm
```

Expect: bounded retries then explicit job failure with a SAFE error code;
**no fabricated score** (WS02/WS05 invariant); user sees recoverable failure
copy; usage ledger records `failed` attempts without inventing success.

## DR-4 — Restart Redis

```bash
docker compose -f docker-compose.prod.yml restart redis
```

Expect (persistence: AOF enabled in compose): rate-limit counters and job
queues survive or degrade exactly per policy; `RATE_LIMIT_FAIL_CLOSED=1`
behaviour observable only while Redis is DOWN (brief 503 window on
heavy/credential routes), not after restart; queued jobs resume; no auth
bypass during any phase (sessions are DB-backed, not Redis).

## DR-5 — Simulate object/audio store failure

```bash
docker compose -f docker-compose.prod.yml stop api
# chmod 000 the audio store directory on the host volume, start api, submit ASR
docker compose -f docker-compose.prod.yml start api
```

Expect: upload → explicit validation/500-safe error, no orphaned job rows
serving forever (jobs expire via `JOB_RETENTION_HOURS`), static app + all
non-audio flows unaffected (audio store is deliberately not an app
dependency).

## DR-6 — Static app + safe error behaviour

```bash
curl -fsS https://<staging>/            # static shell serves
curl -s  https://<staging>/api/health   # 200 {"ok":true,...}
curl -s  https://<staging>/api/account/profile   # unauth → 401 JSON, no stack
curl -s  https://<staging>/legal/privacy.html    # legal pages reachable
```

## DR-7 — No auth bypass under failure (paired with any drill above)

While a dependency is degraded, probe: `/api/history/attempt/<foreign-id>`,
admin routes without admin session, unsafe POST without CSRF token.
Expect: identical 401/403/404 semantics as healthy state. **Fail-closed is
the invariant — degraded must never mean open.**

## Drill log

| Date | Drill | Build SHA | Observed | Gaps filed | Operator |
|---|---|---|---|---|---|

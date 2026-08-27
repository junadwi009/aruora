# 01 — Target Architecture

## Architectural stance
Keep the current modular monolith. The highest-value production split is **process/workload separation**, not domain microservices.

### Keep
- React/Vite frontend.
- Flask API and current route/domain/repository boundaries.
- SQLAlchemy + Alembic.
- Central LLM gateway abstraction.
- Same-origin web/API reverse proxy.

### Add
- Redis for server-side sessions, distributed rate limiting, queue/broker state, short-lived locks, and idempotency records.
- Background workers for CPU-heavy ASR and expensive/slow LLM jobs.
- Object storage or a secure ephemeral blob handoff for audio when API and workers do not share local storage.
- Production-grade telemetry and backup/recovery.
- Selective Auto-RAG using pgvector + PostgreSQL full-text search, with an ingestion worker and retrieval service.

## Runtime components
### 1. Edge / reverse proxy
Responsibilities:
- TLS termination;
- HTTP→HTTPS redirect;
- request body limit;
- slow-client buffering;
- security headers;
- `/api` reverse proxy;
- static caching for hashed web assets;
- no public database/Redis/API-worker ports.

Use an existing managed load balancer/CDN or Nginx/Caddy/Traefik. Do not bind the WSGI server directly to the public internet.

### 2. Web
Static Vite build served by edge/Nginx. `VITE_API_BASE` should be empty/same-origin in production.

### 3. API
Flask handles:
- authentication/authorization;
- validation;
- lightweight CRUD;
- job submission/status;
- deterministic essay metrics that are fast enough for request path;
- signed upload/download orchestration.

The API should not perform long CPU ASR inside the request worker after the queue migration.

### 4. Redis
Separate logical namespaces/prefixes for:
- `session:*`
- `ratelimit:*`
- `idempotency:*`
- `celery:*` or equivalent queue keys
- short-lived job-status/cache data

Production Redis must require authentication/TLS when crossing host boundaries and must not be public.

### 5. PostgreSQL
Prefer a managed PostgreSQL service for production-standard deployment. If self-hosted, backups, encryption, monitoring, upgrades, and restore testing become first-party responsibilities.

No browser or worker should connect using an owner/superuser role.

### 6. Workers
Recommended queues:
- `llm-score`: Writing/Speaking text evaluation.
- `llm-generate`: reading/listening/vocab/lesson generation.
- `asr`: transcription/audio analysis; low concurrency, CPU/GPU constrained.
- `mail`: verification/reset/reminder mail.
- `maintenance`: retention, cleanup, rollups.

Workers call domain/services, not Flask route functions.

### 7. Object storage
Needed once queued audio may be processed on another machine/container. Requirements:
- private bucket/container;
- server-side encryption;
- random object IDs;
- no public listing;
- short lifecycle for raw audio;
- signed URLs or service credentials only;
- deletion on successful/failed job cleanup according to retention policy.

### 8. Auto-RAG knowledge layer

Responsibilities:
- approved-source registry and change detection;
- versioned parsing/chunking/embedding;
- PostgreSQL full-text + pgvector retrieval;
- namespace/allowed-use/authorization prefilters;
- optional reranking;
- context packing and provenance;
- retrieval evaluation and source freshness.

The RAG layer is used by Aura/help and background Task Pool generation. It is not used for exact learner state, authorization, deterministic scoring logic, or every task serve.

```text
Approved sources → ingestion worker → PostgreSQL/pgvector/FTS → retrieval service → LLM gateway
                                                         ↘ provenance → Task Bank
```

## Deployment profiles
### Profile A — Public beta, cost-minimized
Acceptable only with careful limits:
- 1 hardened VM;
- reverse proxy;
- separate API + worker containers;
- PostgreSQL and Redis preferably managed; if local, backup off-host;
- external object storage;
- monitoring from outside the VM.

This profile avoids Kubernetes while providing workload isolation and off-host recovery.

### Profile B — Production standard
- managed edge/TLS;
- multiple API replicas;
- managed PostgreSQL with automated backup/PITR;
- managed Redis;
- independent worker scaling;
- object storage;
- centralized observability;
- staging environment using the same topology class.

## Network policy
Public:
- `443/tcp` only (plus `80` redirect if needed).

Private:
- API;
- worker control;
- PostgreSQL;
- Redis;
- metrics exporters.

Admin tools must not be exposed as unauthenticated public services.

## Failure behavior
- Redis unavailable: authenticated session-dependent endpoints fail safely; do not bypass auth. Health/readiness should report degraded/unready.
- LLM provider unavailable: return/retry job as a controlled failure; never return fake score.
- ASR unavailable: preserve job and expose retryable status within limits.
- PostgreSQL unavailable: API readiness fails; static frontend may show service unavailable.
- Object storage unavailable: reject new audio jobs rather than accepting data that cannot be processed safely.

## ARUORA product-domain modules

Keep one deployable API initially, but make boundaries explicit in code/services:

```text
identity/account
learner profile + Destination
evaluation/scoring
Journey/recommendation
practice/content
progress/readiness
analytics/cohort events
notification preferences
Study Pool preference (opt-in only initially)
```

Future-gated modules:

```text
Study Pods/community
WhatsApp provider adapter
human help/tutor supply
payments
additional language/exam tracks
```

Do not create microservices merely to mirror these modules.

## Product-event flow

Authoritative completion events should be emitted server-side after successful persistence, then consumed asynchronously for analytics/notifications where possible. Analytics failure must not roll back a completed learning action.

## Multi-track compatibility

Keep global account/consent/acquisition/communication concepts independent from IELTS-specific attempt/rubric/band tables. This prepares for future ARUORA tracks without pretending IELTS curriculum/scoring can be generalized today.

## Scaling signals
Scale API on request concurrency/latency, not ASR CPU.
Scale ASR worker on queue depth + processing time.
Scale LLM worker on provider concurrency/rate limits + queue age.
Scale DB only after observing pool saturation/slow queries.

Do not infer scale needs from registered-user count alone.

## Shared Task Pool and AI economy

Add an explicit content-inventory path:

```text
practice request
  → task-selection service
  → validated task bank
  → task exposure row
```

and a separate replenishment path:

```text
inventory monitor
  → generation queue
  → LLM generator
  → validators/deduplication
  → activation/quarantine
```

`llm-generate` workers should primarily replenish shared inventory. Standard practice routes should not call them synchronously on every learner request.

Add an append-only AI usage ledger fed by workers/gateway responses. Redis counters may enforce fast budgets, but PostgreSQL usage records are the auditable source for provider/model/token/cost reporting. See `27_AI_TOKEN_ECONOMY_AND_TASK_POOLING.md`.


## Knowledge-plane failure behavior

- RAG outage must not prevent login, profile access, pooled task serving, deterministic readiness math, or previously available Task Bank content.
- Aura/help may degrade to curated static help or an explicit unavailable response.
- Pool replenishment pauses instead of generating ungrounded content when a use-case requires RAG.
- Last known-good active source/index version remains available if a new ingestion version fails validation.

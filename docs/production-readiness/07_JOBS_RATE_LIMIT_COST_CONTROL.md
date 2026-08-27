# 07 — Jobs, Distributed Rate Limiting, and Cost Control

## Goal
Prevent LLM/ASR/email features from exhausting CPU, provider quota, or money, and make slow work reliable under multiple API workers.

## Current baseline
The reviewed limiter is intentionally in-process and documents that effective limits multiply with Gunicorn workers. That is acceptable for small self-hosting, not public production.

## Dependencies
WS03 for server-side identity/session, WS04 for user ownership, WS08 for DB patterns.

## WS07 ownership
Expected areas:
- replace/extend `api/app/ratelimit.py`
- Redis client/config
- job service/models/status endpoints
- worker bootstrap/config
- routes that currently call long LLM/ASR synchronously
- abuse/cost tests

## Task WS07-01 — Shared Redis-backed limits
Rate limits must work across all API replicas/workers.

Key dimensions:
- IP/network signal for unauthenticated surfaces;
- normalized account/email hash for login/recovery abuse;
- authenticated user ID for paid/heavy features;
- endpoint/action bucket;
- optional device/session signal.

Do not key expensive authenticated usage by IP alone because NAT users share addresses and attackers can distribute IPs.

## Task WS07-02 — Separate abuse limits from product quota
Maintain distinct concepts:
- **rate limit**: short-window abuse/DoS protection;
- **concurrency limit**: active heavy jobs per user;
- **daily/monthly quota**: product entitlement/cost control;
- **provider budget**: global spend ceiling/alert.

Returning `429` should expose retry metadata where safe, but not internal quota architecture.

## Task WS07-03 — Job abstraction
Create a job record/contract with:
- `id` random/unguessable;
- `user_id`;
- `type`;
- `status` (`queued/running/succeeded/failed/cancelled/expired`);
- progress where meaningful;
- created/started/completed timestamps;
- idempotency key;
- result reference or validated result;
- safe error code (not provider secret/raw stack trace);
- provider/model metadata for LLM work;
- retry count.

Job status lookup must be user-scoped.

## Task WS07-04 — Queue split
At minimum:
- ASR queue with low concurrency;
- LLM scoring queue;
- LLM generation queue;
- mail queue.

Heavy queues must not share all worker slots with critical security mail or ordinary requests.

Celery + Redis is a reasonable fit for the current Python stack, but another mature queue is acceptable if it meets the acceptance criteria. Do not introduce two queue frameworks.

## Task WS07-05 — Idempotency
For paid/heavy POST operations:
- client generates or receives an idempotency key;
- server binds it to user + operation + canonical request hash;
- duplicate submission returns the existing job/result;
- keys have bounded retention;
- a key reused for a different payload is rejected.

This prevents browser retry, double-click, network replay, and frontend polling bugs from generating duplicate provider charges.

## Task WS07-06 — Retry policy
Per job type define retryable errors.

LLM:
- retry selected 429/5xx/network timeouts;
- bounded attempts with exponential backoff + jitter;
- no retry on invalid model output without an explicit repair policy/cap;
- no infinite provider fallback loops.

ASR:
- retry transient object-store/worker infrastructure failures;
- do not repeatedly retry corrupt/unsupported audio.

Mail:
- retry transient transport failures;
- suppress after bounded attempts and expose operational alert.

## Task WS07-07 — Backpressure
When queue age/depth exceeds thresholds:
- reject or defer new heavy jobs with a clear retryable response;
- preserve ordinary account/history endpoints;
- expose operational metrics and alerts;
- do not autoscale without an upper bound that can create uncontrolled provider spend.

## Task WS07-08 — Cost accounting
Implement WS27's append-only AI usage ledger and derive fast quota/rollup counters from it. Track per user/day/month and globally:
- pool serves separately from provider calls;
- fresh generation, validation, scoring, Aura, and ASR as distinct operations;
- provider/model requested and actually used;
- input/output/reasoning/cached/cache-write tokens where returned;
- provider-reported actual cost where available plus cost-source metadata;
- failed/retried-call cost where applicable;
- cache hit/miss status where applicable;
- ASR processing seconds/remote cost.

`GenUsage.count` may remain temporarily for compatibility but must not be the final billing/cost source of truth. Do not decrement a fresh-generation quota simply because a user was served an already-pooled task.

Set budget alarms and a hard global emergency kill-switch for paid inference while keeping pooled practice and non-AI account/export/delete functionality available where safe.

## Task WS07-09 — Abuse escalation
Suggested ladder:
1. normal rate limit;
2. progressive delay/tighter bucket after repeated failures;
3. challenge/user verification for suspicious anonymous flows where appropriate;
4. temporary risk hold;
5. admin review/block for sustained abuse.

Do not make CAPTCHA the only line of defense, and do not permanently lock an account because an attacker generated failures against it.

## Founding Beta cost policy

“Free during Founding Beta” is a commercial/product statement, not an infrastructure promise of unlimited compute.

Implement separate limits for:
- authentication abuse;
- API request abuse;
- LLM scoring/generation quota;
- ASR/audio minutes;
- queued jobs per user;
- optional notification/WhatsApp spend later.

Expose friendly quota messaging that preserves the ARUORA tone without hiding the limit.

Cost dashboards should be segmentable by `cohort_id` and feature, but not leak raw learner text.

## Required tests
- two API processes share the same effective Redis limit;
- User A quota does not consume User B quota;
- duplicate idempotency key returns same job;
- same key + different payload rejected;
- queue overload does not break login/profile/history;
- failed job cannot leak provider stack/key;
- user cannot read another user’s job ID;
- budget kill-switch prevents new paid jobs but leaves account deletion/export reachable.

## Exit criteria
Rate limiting is distributed, heavy operations are bounded and queueable, duplicate requests are idempotent, and there is a documented hard ceiling for AI cost and ASR resource use.

## Task WS07-10 — Shared content generation budget

Coordinate with WS27:
- `llm-generate` becomes primarily an inventory-replenishment queue;
- one distributed replenishment lock/idempotency key exists per pool bucket/generation epoch;
- background generation obeys a separate budget envelope from learner scoring;
- when budget pressure occurs, experimental/low-demand replenishment stops before calibrated scoring is silently downgraded;
- pool depletion must not cause an unbounded synchronous generation storm.

Recommended cost precedence under pressure:
1. protect auth/non-AI core;
2. continue already-pooled practice;
3. preserve product-policy-approved calibrated scoring while budget remains;
4. reduce/defer low-priority replenishment and experimentation;
5. fail paid AI calls explicitly when the hard cap is reached.

Full selection, inventory, schema, and amortized-cost strategy: `27_AI_TOKEN_ECONOMY_AND_TASK_POOLING.md`.

## Current pool-cap migration rule

The current `_gencap.serve_or_generate()` increments a learner's daily generation count when that learner happens to trigger creation of a shared `GeneratedSet`. Do not preserve that accounting semantics in public production.

Migration rule:
- shared pool replenishment is a **system/background** cost center;
- a learner entitlement is decremented only for an explicitly learner-owned custom generation/evaluation according to plan policy;
- standard pool serve is separately counted but is not a billable generation event;
- pool underfill should enqueue replenishment rather than creating N synchronous learner-triggered generations under concurrent traffic.


## Task WS07-11 — Auto-RAG jobs and budgets

Coordinate with WS28. Add queue/job classes for source sync, document ingestion, embedding backfill, and retrieval evaluation. Each is idempotent by `(source_id, source_version, embedding_version)` or an equivalent stable key.

AI/cost accounting distinguishes at least:
- `embedding_ingest`;
- `embedding_query`;
- `rag_rerank`;
- `rag_answer`;
- `rag_task_generation`;
- `rag_validation`.

A scheduled sync that detects unchanged content must not create new embedding usage. Apply global daily/monthly budget guards to optional reranking and external embedding providers.

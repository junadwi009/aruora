# 10 — Observability, SRE, and Operational Audit

## Goal
Make failures visible before users report them, while ensuring telemetry itself does not become a PII/secret leak.

## WS10 ownership
Expected areas:
- logging configuration/middleware
- OpenTelemetry instrumentation
- metrics endpoints/exporters
- health/readiness
- audit-event persistence
- dashboards/alerts/runbook links

## Task WS10-01 — Structured logs
Use structured JSON in production with fields such as:
- timestamp;
- level;
- service/component;
- request/correlation ID;
- route template, method, status;
- duration;
- user ID as internal numeric/opaque identifier where necessary, not email;
- job ID;
- error class/code;
- deployment version/commit.

Never log by default:
- passwords;
- session IDs/cookies;
- access/reset/verification tokens;
- API keys;
- DB URLs;
- raw essays/transcripts/audio;
- full request bodies;
- sensitive PII.

Security/session correlation may use a one-way keyed/hash representation when justified.

## Task WS10-02 — Distributed tracing
Instrument API, DB, Redis, queue, worker, object storage, and LLM-provider calls with OpenTelemetry-compatible traces.

Propagation:
`edge → API → queue/job → worker → provider/storage`

Trace attributes must not include raw learner content or secrets.

## Task WS10-03 — Metrics
Core API:
- request rate;
- latency histograms by route template;
- status/error class;
- active requests;
- process CPU/memory.

DB:
- pool in-use/wait;
- connect errors;
- query latency/slow query count;
- storage/connection saturation via provider/exporter.

Redis/queue:
- connection errors;
- queue depth;
- oldest-job age;
- running jobs;
- retry/failure/dead-letter count.

AI:
- calls by task/model;
- latency;
- 429/5xx/schema-invalid rate;
- input/output tokens;
- provider-reported/normalized cost;
- cached/reasoning token usage where available;
- provider cache hit/miss;
- calibration version;
- score-distribution drift monitoring without exposing content.

ASR:
- audio duration;
- processing time ratio;
- decode failure;
- silence/quality rejection;
- queue age.

## Task WS10-04 — Error reporting
Use a protected error aggregation service or equivalent with:
- environment/release tags;
- source maps where appropriate;
- PII scrubbing;
- request-body capture disabled by default;
- alert deduplication.

## Task WS10-05 — Security audit log
Separate operational log from durable audit events.

Audit at least:
- login success/failure summary;
- password reset completed;
- email verification;
- session revoke-all;
- role/admin change;
- admin account deletion/reset action;
- user export/delete request and completion;
- security-control changes;
- production deployment/migration ID.

Do not store session/reset tokens in audit records.

## Task WS10-06 — SLO dashboards
Create dashboards for:
- availability/error budget;
- non-AI API P50/P95/P99;
- AI/ASR queue age and completion latency;
- provider failure/cost;
- DB/Redis health;
- auth failure spikes;
- backup freshness;
- deployment markers.

Provisional targets come from `00_MASTER_ROADMAP.md`; revise after load testing/real traffic.

## Task WS10-07 — Alerts
Page/urgent:
- sustained 5xx/error-budget burn;
- database unavailable;
- Redis unavailable if sessions depend on it;
- queue age beyond user-visible threshold;
- provider cost exceeds emergency threshold;
- backup stale/failed;
- disk nearly full for self-hosted stateful services;
- repeated worker crash loop.

Ticket/non-page:
- calibration drift warning;
- dependency scan findings;
- growing slow-query rate;
- moderate auth abuse.

Avoid alerting on every single user validation error.

## Task WS10-08 — Synthetic monitoring
From outside production infrastructure periodically verify:
- landing page;
- API liveness;
- sign-in page/static assets;
- a non-destructive authenticated synthetic path in staging or a dedicated synthetic production account;
- queue round trip if safe/cost-bounded.

Do not use a privileged admin account for synthetic monitoring.

## Task WS10-09 — Privacy-safe analytics
If product analytics are added:
- document purpose;
- minimize identifiers;
- avoid raw learner content;
- respect consent/cookie requirements by jurisdiction;
- separate product analytics from security logs.

## Product observability and WML

Operational telemetry and product analytics serve different purposes but must share stable correlation identifiers.

Dashboards should include:
- registration/onboarding/placement conversion by cohort;
- first meaningful session;
- D1/D7 meaningful return;
- WML;
- scoring/LLM/ASR failure rate;
- queue latency;
- AI cost per meaningful learner;
- Study Pool opt-in only after available.

Do not copy essay/transcript/audio content into traces, analytics, or error breadcrumbs.

Alerting remains operational, not growth-oriented: a fall in D7 is a product investigation; cross-user authorization failure or score corruption is an incident.

## Exit criteria
Every production request/job can be correlated without logging secrets/content, core dependencies and AI cost are observable, backup freshness is monitored, and alert/runbook ownership exists before launch.

## Task Pool / AI-economy dashboard

Add dashboards for:
- active/validating/quarantined task count by priority bucket;
- pool hit/fallback/depletion rate;
- learner recent-repeat rate;
- global item-exposure skew;
- generation accepted/rejected/duplicate rate;
- generation cost per accepted task;
- amortized shared generation cost per serve;
- AI cost by operation/model/provider/cohort;
- scoring cost per completed evaluation;
- AI cost per WML and activated learner;
- retry cost and cache savings.

Alert on pool depletion for high-demand buckets and unusual generation/retry spend. A healthy web API with an empty task pool is a product incident even if HTTP 200 metrics look normal.


## Auto-RAG observability

Add dashboards/alerts for:
- source sync freshness and failures;
- active/staged/quarantined sources;
- chunk counts by namespace;
- retrieval latency and zero-result rate;
- frozen-benchmark Recall@K / Precision@K;
- ANN-vs-exact recall samples when HNSW is enabled;
- unsupported-claim/grounding regression;
- embedding/rerank/RAG costs;
- source near-copy rejection in generated tasks;
- any authorization-filter failure as a security incident.

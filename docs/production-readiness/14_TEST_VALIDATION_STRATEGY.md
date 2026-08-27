# 14 — Test and Validation Strategy

## Goal
Define evidence required to claim production readiness. “Unit tests pass” is necessary but not sufficient.

## Test pyramid / layers
### Layer 1 — Pure unit tests
Fast, deterministic:
- IELTS rounding/leveling;
- answer normalization;
- SM2/lesson logic;
- schema validation;
- token/quota calculations;
- prompt payload builders that prove learner text stays outside system instructions.

### Layer 2 — Repository/database tests
Use PostgreSQL for production semantics:
- ownership scoping;
- cascade deletion;
- unique constraints;
- migrations;
- transaction behavior;
- job/idempotency records.

### Layer 3 — API integration
Real Flask + Postgres + Redis with stubbed external providers:
- auth/session/CSRF;
- BOLA matrix;
- rate limits across shared store;
- job submission/status;
- export/delete;
- error contracts.

### Layer 4 — Browser E2E
Playwright critical user journey against production-like stack.

### Layer 5 — AI regression/evaluation
Frozen calibration set and adversarial prompt suite.

### Layer 6 — Load/resilience/security
Staging-only or controlled environment.

## Mandatory suites
## TV-01 — Scoring correctness
Regression against official rounding examples and internal criterion semantics.

## TV-02 — Multi-user authorization
For every user-owned ID route, User B cannot read/change/delete User A’s object. Include nested resources and jobs.

## TV-03 — Authentication/session
- login/logout;
- session rotation;
- server revoke;
- idle/absolute timeout;
- reset single-use;
- email verification;
- admin authorization;
- CSRF.

## TV-04 — LLM contracts
For every task:
- valid stub schema accepted;
- missing/wrong fields rejected;
- out-of-range band rejected;
- unexpected huge arrays/strings rejected;
- prompt-injection payload cannot alter system/user role construction;
- invalid provider JSON does not persist a score.

## TV-05 — Migration matrix
At minimum:
- empty DB → head;
- previous supported revision/snapshot → head;
- current app boots and runs smoke after migration;
- failed migration procedure documented/tested where feasible.

## TV-06 — Backup/restore
Restore isolated copy and run integrity + app smoke. Record date, backup ID, RPO/RTO, operator, result.

## TV-07 — Load tests
Use k6, Locust, or equivalent. Define scenarios, not just one endpoint.

Initial scenarios:
1. login/profile/history mix;
2. concurrent writing job submissions under per-user limits;
3. ASR queue burst;
4. Redis rate-limit contention;
5. progress/history with realistic row counts.

Provisional acceptance for beta:
- non-AI P95 <500 ms at the agreed expected concurrency;
- no cross-user failures;
- no uncontrolled 5xx growth;
- queue backpressure activates before API starvation;
- DB connections stay under configured budget;
- cost quota remains exact across replicas.

Do not invent a “10,000 concurrent users” target without a business traffic model.

## TV-08 — Resilience tests
In staging:
- stop one API replica;
- restart worker during job;
- temporarily deny LLM provider;
- restart Redis according to persistence expectations;
- simulate object-store failure;
- verify static app + safe error behavior;
- verify no auth bypass occurs.

## TV-09 — Security tests
Automated/static:
- CodeQL/dependency/container/secret scan.

Dynamic/manual priorities:
- BOLA;
- CSRF;
- session fixation/revocation;
- password reset reuse/enumeration;
- forwarded-header spoofing;
- Host header reset-link poisoning;
- oversized upload/body;
- admin function authorization;
- prompt injection + improper LLM output handling;
- stored/reflected content rendering safety.

For GA or material revenue/PII scale, schedule an independent penetration test if feasible.

## TV-10 — AI scoring calibration
Writing:
- human-adjudicated set;
- exact and ±0.5 agreement;
- MAE;
- ordinal agreement metric;
- criterion-level error;
- repeated runs;
- model/prompt comparison.

Speaking:
- separate text-only and audio-supported evaluations;
- pronunciation agreement only when audio evidence exists;
- microphone/noise robustness;
- subgroup/accent analysis when lawful and statistically meaningful.

No universal numeric pass threshold is asserted by this pack because the acceptable error depends on product claim and dataset quality. The team must set thresholds **before** evaluating a candidate release to avoid moving the goalposts.

## TV-11 — Accessibility
Critical pages:
- automated axe-equivalent;
- keyboard-only E2E;
- focus management;
- labels/errors;
- zoom/reflow;
- one manual screen-reader smoke before major release.

## TV-12 — Product funnel and cohort integrity

Test:
- server assignment/validation of cohort and acquisition source;
- goal/target/deadline persistence and deletion;
- meaningful-action event deduplication;
- WML computation on fixed fixtures;
- lecturer and LinkedIn cohorts remain separable;
- analytics excludes raw essays/transcripts/audio.

## TV-13 — ARUORA brand/claim regression

Test critical screens for:
- ARUORA naming;
- current estimate vs official-score wording;
- Destination/Target/Next Action hierarchy;
- no unsupported Readiness percentage;
- Aura low-confidence/failure copy;
- reduced motion and keyboard behavior.

## TV-14 — UAT evidence protocol

Before each cohort expansion, attach:
- cohort definition;
- build SHA;
- deployed environment;
- P0/P1 count;
- funnel metrics;
- product interview summary;
- known bias/limitations;
- explicit GO/NO-GO decision.

## TV-16 — Auto-RAG retrieval and ingestion

Maintain a frozen retrieval set with expected source/chunk IDs and authorization filters. Test:
- unchanged source → no duplicate chunks/embedding cost;
- changed source → staged version, canary, atomic activation;
- failed new version leaves prior ACTIVE version intact;
- namespace/allowed-use/tenant filtering;
- exact term and semantic paraphrase retrieval;
- hybrid retrieval quality;
- Recall@K / Precision@K and exact-vs-ANN recall when applicable;
- retired/quarantined chunks never returned;
- indirect prompt injection from retrieved content;
- SSRF and malicious URL ingestion;
- RAG-generated task provenance and source near-copy rejection;
- normal pooled-task serve generates no RAG/LLM usage event.

## Release evidence bundle
For each release candidate retain:
- git SHA/image digest;
- CI result links;
- migration revision;
- security scan summary;
- E2E summary;
- load-test report;
- calibration report/model+prompt version;
- backup freshness + last restore drill;
- known accepted risks;
- approval decision.

## Exit criteria
A release decision can be reproduced from test evidence, not intuition or a screenshot walkthrough.

## TV-15 — AI usage ledger and Task Pool

Required integration tests:
- serving an existing pooled task creates no billable generation event;
- one provider call creates one auditable usage event with provider/model/token/cost fields where returned;
- retries are linked and not mistaken for new learner benefit;
- budget hard stop prevents new paid generation while pooled practice remains usable where safe;
- unseen tasks are preferred and cooldown prevents immediate repeats;
- retired/quarantined/wrong-exam-variant tasks are never served;
- answer keys cannot be bulk-fetched before authorized reveal;
- simultaneous replenishment attempts coalesce/idempotently lock per bucket;
- invalid/duplicate generated content never becomes ACTIVE;
- generated/rejected items are both represented in generation economics;
- scoring model cannot be silently substituted by cost fallback outside calibration policy.

Load test the pool selector with realistic exposure history; do not use database-wide `ORDER BY random()` as the only production selection design.

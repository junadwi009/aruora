# PR 18 — reliable evaluation and dependency remediation

## Release status

Draft repair, not a production release. This document describes implementation,
not a claim that tests or deployment have passed. Exact CI evidence is recorded
in the PR handoff after validation. Do not merge while required security checks
are red. Do not expose a production/UAT instance before the remaining gates close.

## Evaluation contract

When Redis is configured, POST /api/writing/evaluate and
POST /api/speaking/evaluate require an Idempotency-Key (8–64 alphanumeric,
underscore or hyphen characters). They return HTTP 202 and a jobId. The browser
polls GET /api/jobs/<id>, or recovers a missing receipt with
GET /api/jobs/lookup?type=score_writing&key=<key> (equivalent for speaking).
Every lookup is scoped by authenticated user. Legacy development requests without
a key retain the inline HTTP 200 contract only when Redis is not configured.

Same account + same key + same validated input/language returns the same job.
Reusing that key with different input is HTTP 409. Keys are retained only for the
job-retention window (currently configured by JOB_RETENTION_HOURS); do not claim
indefinite exactly-once operation. Admission bounds queued + running evaluations
per account under a PostgreSQL profile-row lock. Provider calls run in Celery,
not the Gunicorn Writing/Speaking request. Other legacy AI routes (notably
placement and roleplay turns) still contain synchronous work.

The browser retains only a key/job reference in sessionStorage, namespaced by
account and skill. No essay or transcript is stored there. A reload offers to
check the existing request, not silently resubmit. Creating a separate request
requires explicit confirmation when a prior outcome is unknown. Draft text is
still screen-local: a receipt is not an autosaved draft.

## Delivery and crash semantics

Migration b26c20261005 adds job_dispatch, a durable dispatch intent created in the
SAME transaction as its Job. It backfills queued jobs only. Publishers lease
intents with a bounded delay; broker failures leave them eligible for recovery.
The maintenance queue runs recovery separately from inference/ASR. Messages carry
only the opaque job ID, not learner content. A compare-and-set queued→running
transition admits one execution despite duplicate deliveries. Completed scoring
persists the learner Attempt and job result in one transaction and removes raw
pending input. Pending authored evaluations are included in account export;
account/job deletion cascades into dispatch intents.

Delivery is at-least-once, not a guarantee of exactly-once provider billing.
A job stuck running beyond 900 seconds is failed as JOB_OUTCOME_UNCERTAIN, NOT
re-enqueued. An external request may have completed before a crash. The learner
must check saved progress before deliberately starting new work. Do not use the
old requeue_stale_jobs name as evidence that paid jobs are replay-safe.

## Cost, privacy and scoring boundaries

All gateway score/generate entry points now check the shared kill-switch, and
queued scoring rechecks account existence, email ownership and budget immediately
before inference. Queued replenishment rechecks on each retry. This is NOT an
atomic global budget-reservation system: simultaneous calls may overshoot a
threshold and pre-existing routes do not all record complete provider cost
metadata. External provider spend limits remain necessary. No model ID, rubric,
score normalization, or deterministic metrics algorithm was intentionally changed.

No production credentials, real learner fixtures, or provider keys are included.
Tests use synthetic accounts and the offline stub. Security mail still uses the
existing synchronous SMTP path; a reserved `mail` queue is not proof of async
mail delivery.

## Dependency findings

The candidate frontend lock was generated with npm 11 after npm 10's resolver
failed with `edgesOut`. Vitest is upgraded from 3.x to 4.1.11, the patched version
listed by the upstream advisory. Other direct dependency ranges were retained;
the lock resolves fresh compatible releases. Re-run TypeScript, tests, build and
npm audit on the committed lock, not only the candidate artifact.

NLTK 3.10.3 remains a **blocking, unwaived** Python finding (PYSEC-2026-3740 /
GHSA-8mgp-746c-j5xp). At investigation time the upstream advisory lists no patched
release. The advisory concerns raw model import/export paths; this application
uses linguistic-metric dependencies, not a user-selectable model-file API.
That observation is not a complete transitive reachability proof. Do not claim
NLTK is safe, remove it while silently degrading metrics, fake a version, or
ignore the advisory to force a green workflow. A reviewed upstream fix or a
calibration-preserving dependency replacement is still required.

Primary references:
- https://github.com/nltk/nltk/security/advisories/GHSA-8mgp-746c-j5xp
- https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9
- https://docs.celeryq.dev/en/stable/userguide/tasks.html

## Production-like UAT configuration and rollback

Use ops/uat.env.example as the configuration inventory; never commit the populated
.env. The production Compose file forces APP_ENV=production, secure cookies,
an explicit HTTPS origin/host allowlist and isolated internal Redis/PostgreSQL.
It binds web to loopback by default, expecting a separately configured TLS edge.
An explicit one-shot migrate service must complete before API/worker startup.
Fixtures are mounted read-only for initial seeding and stub-mode operation.
Review trusted proxy hop counts on the actual host. SMTP is required by default;
mail-disabled stub testing must be an explicit isolated test configuration.

worker-infra has been replaced by worker-asr and worker-maintenance. Stop old
workers when promoting this topology; do not leave an old-version consumer on
shared queues. Deploy code, database schema and browser bundle together, with a
verified backup. Before downgrade: stop producers and consumers, inspect/drain
pending jobs, back up, then downgrade to a12c20260929. Dropping job_dispatch
abandons automatic publication recovery. Never downgrade while new workers run.
No migration or deployment has been executed against a user database here.

Still required: full production-image build/smoke, live mail/Google login, TLS and
proxy inspection, worker health/alerts, backup/restore, calibration/provider
validation, capacity testing and real-device UAT. The new Redis/PostgreSQL canary
uses the application routes and a separate Celery process, but not an external
HTTPS deployment or a paid provider.

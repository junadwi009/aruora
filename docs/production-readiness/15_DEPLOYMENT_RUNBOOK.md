# 15 — Deployment and Incident Runbook

## Goal
Make staging and production changes repeatable, observable, and reversible.

## Environments
Minimum:
- local/dev;
- CI ephemeral;
- staging;
- production.

Staging must use the same major database version, Redis/session/job topology, reverse-proxy behavior, and production build mode. It does not need equal capacity.

## Configuration classes
Keep config separate from image:
- public origin/hosts;
- DB URL;
- Redis URL;
- object storage;
- LLM provider/model IDs;
- mail;
- session/cookie settings;
- quotas;
- telemetry;
- admin/bootstrap settings.

Secrets come from environment secret management and never from repository files.

## Pre-deploy checklist
1. Identify release SHA/image digest.
2. CI required jobs green.
3. Security scan triaged.
4. Alembic head known; migration classified.
5. Backup fresh; risky migration requires verified pre-deploy restore point/snapshot.
6. Provider cost limits configured.
7. On-call/operator has rollback access.
8. Check current incidents/DB capacity/queue backlog.
9. Confirm privacy/legal gates if release changes data collection/provider/branding.

## Migration classifications
### Class A — additive/backward-compatible
Example: add nullable column/index concurrently where supported.
Can normally migrate before app rollout.

### Class B — constraint/backfill
Requires staged process and measured lock/runtime.

### Class C — destructive/semantic
Column/table removal, ownership rewrite, data purge. Requires explicit change plan, backup, and forward-fix/rollback strategy. Never bundle casually with unrelated feature release.

## Standard staging deployment
1. Build immutable API/web/worker images.
2. Apply migration using migration role/job.
3. Start/roll API and workers.
4. Verify readiness.
5. Run smoke + critical Playwright.
6. Run selected job queue test.
7. Verify security headers/cookie attributes.
8. Check telemetry for 15-minute or appropriate observation window through actual execution; do not rely only on “containers healthy”.

## Standard production deployment
1. Announce/start change record if team process exists.
2. Confirm backup and current DB revision.
3. Apply safe migration.
4. Roll API replicas with readiness gate.
5. Roll worker groups separately.
6. Roll static web last or according to API compatibility plan.
7. Run synthetic smoke.
8. Watch errors/latency/DB pool/queue/provider metrics.
9. Mark deploy in telemetry.

For incompatible API/web changes, use compatibility window or feature flag; never rely on all clients updating atomically.

## Production configuration preflight
Before any production container becomes ready, validate configuration as code rather than relying on operator memory.

Required preflight failures:
- blank/default `SESSION_SECRET`;
- default/development database password or missing managed-DB credential;
- `COOKIE_SECURE` not enabled behind the production HTTPS topology;
- missing canonical public application origin;
- missing Redis/session store when public session mode requires it;
- LLM live mode with missing provider credential;
- account email verification/reset enabled without a production mail provider;
- debug/testing/stub flags enabled unintentionally;
- permissive CORS or unreviewed proxy/host-trust configuration.

Repository setup must also be internally consistent: create a root `.env.example` for root Compose, or change Compose/docs to an explicit supported env-file path. Fresh-clone production instructions must be reproducible in staging before release.

## Application rollback
Rollback to previous immutable image if:
- sustained 5xx threshold breached;
- auth/session regression;
- cross-user authorization risk;
- job duplication/cost spike;
- severe frontend blocking regression.

Database must remain compatible with the previous app for normal rollback. This is why expand/contract migrations are preferred.

## Database incident
### Bad migration before traffic
- stop rollout;
- evaluate safe Alembic downgrade only if explicitly supported and non-destructive;
- otherwise forward-fix.

### Data corruption/loss
- stop mutating traffic if necessary;
- preserve forensic state;
- restore into isolated DB first;
- determine recovery point/RPO;
- execute approved recovery;
- run integrity smoke;
- trigger privacy incident process if personal data may be affected/exposed.

## Redis incident
Because Redis becomes session/rate/job infrastructure:
- fail authentication safely rather than bypassing session verification;
- determine whether queued job data is durable/reconstructable from PostgreSQL;
- users may need to reauthenticate after loss;
- avoid treating Redis as the sole durable source of completed learning results.

## LLM provider incident
- activate provider feature-degraded state;
- pause new paid jobs or keep queue bounded;
- do not fake scores;
- fallback model only if it passed the same schema/calibration gate;
- maintain account/history/export/delete functionality.

## ASR incident
- pause/cap audio submissions when queue age exceeds policy;
- retain only bounded short-lived audio objects;
- do not let object-storage TTL delete audio before retry policy ends;
- surface clear job failure/retry status.

## Security incident quick path
1. Contain access/key/session compromise.
2. Rotate affected secrets and revoke sessions when required.
3. Preserve logs/evidence.
4. Determine affected data/users/time window.
5. Engage privacy/legal breach process.
6. Patch/mitigate.
7. Validate before reopen.
8. Post-incident review with corrective actions.

Indonesia PDP notification timelines and GDPR timelines (when applicable) are covered in `12_PRIVACY_COMPLIANCE.md`.

## Emergency AI cost kill-switch
Must be operable without redeploy:
- deny new paid LLM jobs;
- optionally allow existing queued jobs to drain or cancel safely;
- preserve deterministic/offline practice functions;
- alert operator and record audit event.

## Cohort-aware rollout

Prefer controlled exposure rather than one irreversible public launch.

Recommended feature/config flags:
- `UAT_COHORT` or campaign assignment mechanism;
- Aura/rebrand rollout only if rollback is needed;
- Study Pool disabled by default until approved;
- WhatsApp disabled until explicit launch;
- expensive AI features with independent kill switches.

Deployment records must state which cohort/product features were enabled at that SHA.

A production rollback must not silently change scoring semantics for already-persisted attempts; persist scoring/prompt versions so historical results remain interpretable.

## Runbook evidence
After each production incident/change, record:
- release;
- operator;
- migration;
- start/end;
- alerts triggered;
- rollback/forward fix;
- user impact;
- follow-up tasks.

## Exit criteria
Staging and production deployments are scripted/documented, app rollback does not normally require DB rollback, recovery paths are rehearsed, and security/provider/Redis incidents have fail-safe behavior.

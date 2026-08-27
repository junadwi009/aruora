# 08 — Database, Migrations, Backup, and Disaster Recovery

## Goal
Make PostgreSQL durable, upgradeable, recoverable, and safe for schema evolution under real user data.

## Immediate P0 — PostgreSQL 18 volume
The reviewed `docker-compose.prod.yml` mounts:
`ielts_pgdata:/var/lib/postgresql/data`
while using `postgres:18`.

The official image changed PostgreSQL 18+ to a version-specific `PGDATA` under `/var/lib/postgresql/<major>/docker` and changed the declared volume to `/var/lib/postgresql`.

Fix new PostgreSQL 18 deployments to mount the parent:
`ielts_pgdata:/var/lib/postgresql`

Do not blindly change an existing production volume path after data exists. Existing data requires an explicit migration procedure and verified backup.

## WS08 ownership
Expected areas:
- Docker compose DB config
- SQLAlchemy engine/pool config
- Alembic migration policy/tests
- backup/restore scripts/runbook references
- database observability hooks

Ownership/cascade schema is primarily WS04; WS08 integrates operationally.

## Task WS08-01 — Production DB profile
Recommended production-standard:
- managed PostgreSQL;
- encryption at rest;
- private networking/firewall;
- automated backup;
- PITR/WAL capability;
- monitoring;
- minor-version patching policy;
- separate credentials for app/migrations/backup where feasible.

If self-hosted, document how every one of those capabilities is implemented.

## Task WS08-02 — Least-privilege roles
Separate:
- migration/DDL role;
- runtime application role;
- read-only reporting/support role if needed;
- backup role where provider/self-host design requires it.

The runtime app must not connect as PostgreSQL superuser or database owner if avoidable.

## Task WS08-03 — Connection management
Configure and measure:
- `pool_pre_ping`/stale-connection handling;
- pool size/max overflow matched to API replicas and DB connection budget;
- connect/query timeouts;
- transaction rollback on errors;
- statement timeout for web requests where appropriate.

Do not multiply default pool sizes by many replicas until the total is checked against DB capacity. Add PgBouncer only if metrics justify it or the managed provider requires/recommends it.

## Task WS08-04 — Migration discipline
Every schema change:
- Alembic revision committed with code;
- deterministic upgrade;
- tested from empty DB and from current production-like prior revision;
- no `Base.metadata.create_all()` as a substitute for production migration;
- no long table lock surprises without staging test.

Prefer expand/contract:
1. add nullable/new structure;
2. deploy code that supports old+new;
3. backfill;
4. enforce constraint;
5. remove old field in later release.

## Task WS08-04B — Production database configuration invariants
The current compose baseline provides convenience defaults such as the username/database/password `ielts`. Convenience defaults are acceptable only for disposable local development.

Production requirements:
- `POSTGRES_PASSWORD` (or managed-DB credentials) is mandatory and has no insecure fallback;
- application startup/config validation rejects known development/default credentials in production;
- root `.env.example` matches what Compose actually reads; do not document `cp .env.example .env` while only `api/.env.example` exists;
- database secrets are injected by the deployment secret mechanism, not committed or baked into images;
- database URL is never emitted in health responses or logs;
- separate migration/admin credential from the lower-privilege runtime credential where operationally practical.

## Task WS08-05 — Migration CI
CI should prove:
- `alembic upgrade head` on empty PostgreSQL succeeds;
- upgrade from a maintained prior snapshot/revision succeeds;
- ORM metadata and Alembic head are not unintentionally divergent;
- application starts against migrated schema.

SQLite-only unit tests are not sufficient evidence for PostgreSQL migration behavior.

## Task WS08-06 — Backup policy
Minimum public beta:
- daily backup/snapshot;
- encrypted;
- stored off the application host;
- retention schedule documented;
- backup success monitored;
- monthly restore drill initially.

Production-standard:
- PITR/continuous archiving when supported;
- periodic full/base backup + WAL/snapshot retention;
- immutable or deletion-protected copy according to threat model;
- restore into isolated environment and verify application-level data.

A backup that has never been restored is not a proven recovery mechanism.

## Task WS08-07 — Restore verification
Restore test must verify more than “Postgres starts”:
- migrations/head state;
- account can log in in isolated test setup;
- attempts/history/card counts expected;
- FK integrity;
- no orphan rows;
- encrypted secrets are supplied separately, not assumed to exist in backup;
- object/audio references either restore correctly or are intentionally ephemeral.

Record measured RPO/RTO from drills.

## Task WS08-07B — Binary/profile media storage
The reviewed model can store avatar content as a base64 data URL in PostgreSQL. For a public multi-user service, avoid unbounded binary payloads in the primary relational row.

Target:
- validate avatar MIME type and decoded size server-side;
- re-encode/normalize images where supported instead of trusting supplied data URLs;
- store bounded profile media in object storage and persist an owned object key/metadata in PostgreSQL, or enforce a deliberately small DB-backed cap for beta;
- delete the object as part of account deletion;
- use non-guessable object keys and authorization/signed retrieval if media is private;
- prohibit SVG or other active content unless there is a reviewed sanitizer/policy.

## Task WS08-08 — Data lifecycle maintenance
Add jobs/queries for:
- expiring reset/verification tokens;
- expired sessions/idempotency keys (Redis lifecycle separately);
- expired raw audio/object references;
- old job metadata per policy;
- database bloat/maintenance monitoring where self-hosted.

Do not purge learning history without the published retention policy/user controls.

## Task WS08-09 — Index review
At minimum inspect indexes for:
- `(user_id, created_at)` history queries;
- ownership lookups `(user_id, id)` where useful;
- due flashcards;
- job status/user;
- unique normalized email;
- generation usage/quota windows;
- program/milestone ownership path.

Use query plans/slow-query telemetry rather than indexing every column.

## Product-schema sequencing

Recommended schema sequence:
1. fix existing ownership/cascade correctness;
2. add cohort/acquisition and goal/target/deadline fields needed for UAT;
3. add versioned readiness/recommendation records only when their logic exists;
4. add Study Pool preference only after the opt-in UI is ready;
5. defer Pod/community/tutor/payment tables until their validation gate.

Do not create speculative empty social-marketplace schema in the first production migration wave.

Index UAT fields only after query patterns are known; avoid indexing sensitive/high-cardinality free text unnecessarily.

## Task WS08-10 — pgvector and RAG schema

Coordinate with WS28.

- Verify `pgvector` availability in the chosen managed/self-hosted PostgreSQL profile before migration.
- Add extension enablement through controlled migration/provisioning appropriate to provider permissions.
- Introduce versioned source/document/chunk/ingestion/retrieval-provenance tables from WS28.
- Add full-text GIN indexes and vector indexes only after query/corpus measurements justify them; exact vector search remains the reference path for retrieval recall evaluation.
- Embedding-model changes use parallel version/backfill/canary rather than destructive in-place overwrite.
- Backup/restore tests must prove RAG metadata/index state is recoverable or reproducibly rebuildable from canonical source documents.

## Disaster scenarios to rehearse
- bad application deploy, DB unchanged;
- backward-incompatible migration partially applied;
- accidental user/table deletion;
- PostgreSQL host loss;
- corrupted volume;
- Redis loss (sessions/jobs transient state);
- object-store unavailable;
- provider outage does not require DB restore.

## Exit criteria
PostgreSQL 18 storage is correct, runtime credentials are least-privilege, Alembic is the only production schema path, backups are off-host/encrypted, and at least one full restore drill has succeeded before GA.

## AI usage and Task Pool migration notes

WS27 introduces migration pressure around the current `GeneratedSet` and `GenUsage` models. Sequence changes with WS04/WS07; do not let parallel agents create competing ownership migrations.

Preferred migration order:
1. add append-only usage ledger without removing `GenUsage`;
2. add task lifecycle/provenance/exposure structures while preserving current `GeneratedSet` reads;
3. migrate serving routes to the new pool service;
4. backfill/source-tag existing generated sets where possible;
5. deprecate old counters only after no production route/report depends on them.

Token counts and monetary cost should use explicit numeric columns suitable for aggregation; do not bury all financial usage inside opaque JSON. Raw prompts/responses do not belong in the usage ledger.

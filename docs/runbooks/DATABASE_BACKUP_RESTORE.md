# Runbook — ARUORA IELTS Database: Backup, Restore & DR

Workstream: **WS08** (`docs/production-readiness/08_DATABASE_MIGRATIONS_BACKUP_DR.md`).
Applies to the self-hosted `docker-compose.prod.yml` profile. Managed-PostgreSQL
deployments follow the managed equivalents noted inline.

---

## 1. Production DB profile (WS08-01)

For public beta the minimum accepted profile is:

| Capability | Self-hosted implementation | Managed equivalent |
|---|---|---|
| Managed PostgreSQL | `postgres:18` container, dedicated host | provider DB instance |
| Encryption at rest | full-disk/volume encryption of the data volume | provider default |
| Private networking | db/redis/api/worker services stay off the published port mesh (only `web` publishes) | VPC / private endpoint |
| Automated backup | `ops/db/backup.sh` daily cron | automated snapshots |
| PITR / WAL | **not yet available self-hosted** — accepted residual risk for beta; RPO = 24 h (daily). Promote to managed PITR before scale-out | enable PITR |
| Monitoring | backup freshness check (below) + `pg_isready` healthcheck; observability hooks are WS10 | provider metrics |
| Minor-version patching | pin `postgres:18.x` digest; monthly patch window with backup-first rule | provider policy |
| Separate credentials | see §2 | provider roles |

Reject any deployment that boots with development defaults: the API fails
closed on `APP_ENV=production` + default DB credentials / non-PostgreSQL URL
(WS08-04B, `api/app/__init__.py`).

## 2. Least-privilege roles (WS08-02)

- **DDL/owner role** — `POSTGRES_USER` in compose; the only role that runs
  `alembic upgrade head` (Dockerfile CMD via `MIGRATION_DATABASE_URL`).
- **Runtime role** — `POSTGRES_RUNTIME_USER`/`POSTGRES_RUNTIME_PASSWORD`;
  created on first init by `ops/db/init/01-runtime-role.sh` (DML only, no DDL,
  no role admin). The API + workers connect with it via `DATABASE_URL`.
- **Backup role** — the operator's backup identity needs `SELECT` only
  (plus sufficient to lock: use `pg_dump` with the owner or a dedicated
  read-only role).
- The runtime role must never be the DB owner/superuser. `ops/db/init` only
  executes on an **empty volume**; to retrofit role separation on an existing
  deployment, run the same SQL manually, then rotate `DATABASE_URL` and
  restart the api/workers.

Connection budget (WS08-03): each api/worker process uses
`DB_POOL_SIZE` (default 5) + `DB_MAX_OVERFLOW` (default 10). Before adding
API replicas, verify
`processes × (pool_size + max_overflow) < max_connections − headroom`.
Tune with `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_CONNECT_TIMEOUT_S`,
`DB_STATEMENT_TIMEOUT_MS` (0 = off; migrations are unaffected).

## 3. Backup policy (WS08-06)

- **Frequency:** daily `pg_dump -Fc` (03:15 UTC) via cron → `ops/db/backup.sh`.
- **Encryption:** AES-256-CBC/PBKDF2 via `BACKUP_ENCRYPTION_KEY` — **always
  set in production**. Keys live in the deployment secret store, never in the
  backup, never in git.
- **Off-host:** the script's final line is the operator step — copy the
  `.dump.enc` + `.sha256` to object storage/another host (rclone/scp). A
  backup that lives only on the DB host is a failed control.
- **Retention:** local 14 days (`BACKUP_RETENTION_DAYS`); off-host daily × 14,
  weekly × 8, monthly × 12.
- **Monitoring:** off-host freshness check from a second host
  (`newest backup older than 26 h → incident`). Cron mail on non-zero exit.
- **PITR:** not available self-hosted (RPO 24 h). Re-evaluate before
  paid/public scale.

## 4. Restore drill (WS08-07) — monthly

```sh
RESTORE_FILE=/backups/aruora_ielts_<stamp>.dump.enc \
POSTGRES_USER=ielts POSTGRES_PASSWORD=<owner> \
./ops/db/restore-verify.sh
```

The drill restores into an isolated throwaway `postgres:18` container and
checks: `alembic_version` == chain head; accounts exist; attempts/cards/
programs counts plausible; **zero orphaned user-owned rows**; milestone
cascade intact. It prints the measured **RTO** — record it in the log below.
A restore that has never been verified is not a recovery mechanism.

Drill log (append one line per drill):

| Date | Backup stamp | RPO (h) | RTO measured | Orphans | Result | Operator |
|---|---|---|---|---|---|---|

## 5. Migration discipline (WS08-04/05)

- Alembic is the only production schema path. Never `create_all`.
- Every revision ships with its code + tests; CI (`.github/workflows/ci.yml`
  → `migrations` job) proves: empty-DB upgrade to head, `alembic check`
  (ORM ↔ Alembic parity), `downgrade -1` + re-upgrade, app boot against the
  migrated schema, and the migration test suite on PostgreSQL 18.
- The chain must keep exactly **one head**; parallel workstreams merge
  revisions (see `17_PARALLEL_EXECUTION_GUIDE.md`).
- Expand/contract for destructive changes; long-lock DDL is staged-tested
  before production.

## 6. Data lifecycle maintenance (WS08-08)

- `worker-beat` runs `app.jobs.run_maintenance` hourly
  (`MAINTENANCE_INTERVAL_S`). Manual trigger:
  `POST /api/internal/maintenance/run` with `X-Maintenance-Token`
  (empty token = endpoint disabled).
- Purge targets: revoked/expired sessions (`SESSION_RETENTION_HOURS`, 72 h),
  expired one-time tokens (`OTT_RETENTION_HOURS`, 168 h), finished jobs
  (`JOB_RETENTION_HOURS`), raw analytics (`ANALYTICS_RETENTION_DAYS`, 180 d).
- **Never** purged by maintenance: attempts, cards, programs, milestones,
  lessons, mocks, feedback, usage ledger, admin audit. Learning history is
  governed by the published retention policy and account deletion only.
- Redis (sessions/jobs transient state) self-heals; loss is not a DR event.

## 7. Index review (WS08-09)

Existing coverage: ownership lookups (`ix_*_user`), history
(`ix_jobs_user_created`, `ix_ledger_*`), task bank buckets + exposure
(WS27), analytics (`ix_analytics_*`), gen quota (`ix_gen_usage_user_day`).
Known follow-ups for the next schema touch (deferred — WS27 owns the current
Alembic head): `attempts (user_id, created_at)` history queries and
`cards (user_id, due)` due-queue. Revisit with `EXPLAIN`/slow-query
telemetry, not by default-indexing.

## 8. pgvector / RAG schema (WS08-10)

Deferred to WS28 (READY_FOR_DESIGN). Before any RAG migration: confirm the
chosen PostgreSQL profile enables `pgvector`; vector/GIN indexes only after
corpus measurement; backup/restore drills must prove RAG metadata is
recoverable or reproducibly rebuildable from canonical sources.

## 9. Disaster scenario rehearsals

| Scenario | Response |
|---|---|
| Bad app deploy, DB unchanged | redeploy previous image; no DB action |
| Backward-incompatible migration partially applied | `alembic downgrade` to prior head if safe, else restore drill procedure; stage-test first |
| Accidental user/table deletion | restore to isolated env (§4), extract + reinsert owner rows, document in audit |
| PostgreSQL host loss | provision host, restore newest backup (§4), repoint DNS/compose |
| Corrupted volume | stop db service, preserve volume for forensics, restore newest backup |
| Redis loss | restart empty; sessions/jobs re-establish (users re-login) |
| Object store unavailable | audio/ASR is transient by design; degrade Speaking capture, no DB action |
| Provider outage | LLM gateway fail-closed; no DB restore required |

## 10. Acceptance summary

- [x] PostgreSQL 18 volume mounts `/var/lib/postgresql` (P0 fix, new volumes)
- [x] `POSTGRES_PASSWORD` mandatory; dev defaults rejected at boot (APP_ENV=production)
- [x] Least-privilege runtime role tooling (opt-in init + split migration URL)
- [x] Pool/timeouts configurable (WS08-03)
- [x] Migration CI on PostgreSQL 18 (WS08-04/05)
- [x] Backup/restore/verify scripts + this runbook (WS08-06/07)
- [x] Maintenance purge jobs (WS08-08)
- [ ] Monthly restore drill executed with recorded RPO/RTO (operator)
- [ ] PITR decision before scale-out (operator)
- [ ] pgvector provisioning check (WS28)

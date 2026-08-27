# ARUORA IELTS — Test Register (WS14)

Maps every TV-nn from `docs/production-readiness/14_TEST_VALIDATION_STRATEGY.md`
to concrete suites/artifacts. Status vocabulary: COVERED (automated + green) /
PARTIAL / ARTIFACT (protocol delivered, execution pending) / GAP.

Run commands:
- API: `cd api && python -m pytest -q`
- Web: `cd web && npx tsc --noEmit && npm test && npm run build`
- E2E: `cd web && npm run e2e` (production-like stack required)
- Load: `k6 run tests/load/scenarios/<scenario>.js` (see `tests/load/README.md`)

| TV | Layer / requirement | Suites & artifacts | Status | Gap / owner |
|---|---|---|---|---|
| TV-01 | Scoring correctness (rounding, leveling, SM2, schemas, metrics) | `test_placement_scoring.py`, `test_leveling.py`, `test_sm2.py`, `test_schemas.py`, `test_essay_metrics.py`, `test_seed.py`, `test_models.py`; web `band.test.ts`, `pron.test.ts` | COVERED | keep official rounding fixtures frozen (WS02) |
| TV-02 | Multi-user authorization (BOLA matrix incl. nested + jobs) | `test_bola_isolation.py`, `test_repositories.py`, `test_ws08_db_ops.py` isolation probes; per-route suites | COVERED | matrix review when WS20+ adds routes |
| TV-03 | Auth/session (rotation, revoke, timeouts, reset single-use, admin, CSRF) | `test_auth.py`, `test_account.py`, `test_account_data.py`, `test_ws03_identity_security.py`, `test_password_reset.py`, `test_google_auth.py`, `test_security_hardening.py`, `test_admin.py`; web `settings.test.ts` | COVERED | RBAC/MFA is WS03 GA item |
| TV-04 | LLM contracts (stub schema, rejects, injection, no-score-on-invalid) | `test_llm_stub.py`, `test_prompt_injection.py`, `test_prompt_ip_safety.py`, `test_llm_role_separation.py`, `test_security_llm_auth.py`, `test_speaking_estimate_integrity.py`; live gate `test_llm_live.py`; web `outputHandlingGuard.test.ts`, `aura.test.ts` | COVERED | extend per new AI surface (Aura) |
| TV-05 | Migration matrix (empty→head, prev→head, boot smoke, PG semantics) | `test_migrations.py` (SQLite chain + PG variants + downgrade/re-upgrade + boot-on-migrated); CI `migrations` job (PG 18, `alembic check`) | COVERED | app-boot smoke on PG in CI job already included |
| TV-06 | Backup/restore evidence | `ops/db/backup.sh`, `restore.sh`, `restore-verify.sh`; runbook `docs/runbooks/DATABASE_BACKUP_RESTORE.md` | ARTIFACT | first restore drill + RPO/RTO row (operator) |
| TV-07 | Load tests (5 scenarios, thresholds set pre-run) | `tests/load/` (k6 pack: login/history, writing jobs, ASR burst, rate-limit contention, realistic volumes) + `LOAD_TEST_LOG.md` | ARTIFACT | first staging execution + log rows |
| TV-08 | Resilience drills | `docs/runbooks/RESILIENCE_DRILLS.md` (DR-1..DR-7 with expected outcomes) | ARTIFACT | execute in staging; log findings |
| TV-09 | Security: static + dynamic | static: `tests/secret_scan.sh`, `.github/workflows/codeql.yml`, `test_ws09_edge_security.py`, `test_security_hardening.py`; dynamic: BOLA/CSRF/session/reset/header suites (TV-02/03/04 files) | PARTIAL | container scan + dependency audit job (WS11); independent pen test pre-GA |
| TV-10 | AI scoring calibration | `test_calibration.py` (frozen-set machinery); thresholds must be fixed BEFORE evaluation | PARTIAL | human-adjudicated set + pre-registered thresholds (WS02, before any calibrated-score release) |
| TV-11 | Accessibility | web e2e journey exists; a11y assertions/axe not yet | GAP | WS13 (frontend routing/a11y) owns |
| TV-12 | Product funnel & cohort integrity | `test_analytics.py` (event dedup, server-validated cohorts, content-free events), `test_ws08_db_ops.py` purge isolation | PARTIAL | WML fixture-math tests when WS21 lands WML endpoint |
| TV-13 | Brand/claim regression | estimate-vs-official wording asserted in several suites (`test_speaking_estimate_integrity.py`, `aura` tests) | PARTIAL | screen-level claim regression pack (WS23) |
| TV-14 | UAT evidence protocol | protocol defined in `22_UAT_FOUNDING_BETA_RELEASE_PLAN.md`; per-cohort log in `19_IMPLEMENTATION_TRACKER.md` | ARTIFACT | first cohort evidence bundle (WS22) |
| TV-15 | AI usage ledger & Task Pool | `test_ws07_cost.py`, `test_ws07_jobs.py`, `test_ws27_task_pool.py`, `test_efficiency.py` (pool-first, ledger-only-billing, exposure anti-repeat, budget stop) | COVERED | load-test the pool selector (TV-07 pack extension when staging) |
| TV-16 | Auto-RAG retrieval & ingestion | `test_rag.py` (WS28 initial suite) | PARTIAL | frozen retrieval set + staged-ingestion tests mature with WS28 |

## Release evidence bundle

Per-release template: `docs/runbooks/RELEASE_EVIDENCE.md`. A release decision
must be reproducible from that bundle.

## Known stale artifacts (fix with owning session)

- `tests/smoke.sh` greps `llmMode` from `/api/health` — WS09 separated health
  surfaces (`/api/health` no longer returns `llmMode`; it lives under
  `/api/admin/health/detail`). Smoke must be updated (WS11/WS15) and its
  `docker compose` target verified against the current compose file set.

## Change log

| Date | Note |
|---|---|
| 2026-08-27 | Register created; TV-07 k6 pack + TV-08 drills + CodeQL workflow + release-evidence template delivered |

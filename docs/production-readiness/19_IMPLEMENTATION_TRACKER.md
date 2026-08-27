# 19 — Implementation Tracker

Use this file in the integration branch. Keep issue/PR links beside each item.

| Workstream | Status | Branch/PR | Owner | Blocking issue | Last verified |
|---|---|---|---|---|---|
| WS02 Scoring integrity | DONE (integrated commit `fde6b68`; official rounding, cefrApprox, scoring metadata envelope, pronunciation fail-closed, calibration gates, IP guard) | `fde6b68` | integration session | Legal/IP ticket for retained rubric wording pre-public | 2026-08-27 |
| WS04 Multi-user isolation | DONE (integrated `fde6b68`; NOT NULL ownership, schema CASCADEs, scoped lookups, BOLA matrix, ownership inventory) | `fde6b68` | integration session | RLS (WS04-08) deferred by design | 2026-08-27 |
| WS05 LLM security | DONE (integrated `fde6b68`; role separation, output schemas, bounds/retry, audit meta, injection suite, promotion gate) | `fde6b68` | integration session | Provider privacy live-verification (PROVIDER_PRIVACY_REVIEW.md) | 2026-08-27 |
| WS13 Frontend routing/a11y | PARTIAL→core DONE (integrated `9f18d62`: URL deep-links/back-forward via history sync, auth outage fail-closed guard (pre-existing), consistent failure-UX mapping (`lib/apiErrors.ts`), axe-core gates on Welcome/Home + landmark assertions, reset-token URL scrub pre-existing; remaining: full React-Router migration, Playwright keyboard smoke in CI, manual SR/zoom checks) | `9f18d62` | integration session | Playwright-in-CI needs compose stack | 2026-08-27 |
| WS03 Identity/session | BLOCKED by WS04 | | | | |
| WS08 DB/backup/DR | IN PROGRESS (P0 volume fix, WS08-02/03/04B/06/07/08 implemented on `master` working tree 2026-08-27; WS08-09 index migration deferred - WS27 owns the active Alembic head; restore drill pending operator) | - | | WS08-09 indexes chain onto the next stable head; WS28 owns pgvector (WS08-10) | 2026-08-27 |
| WS07 Jobs/rate/cost | IN PROGRESS (core implemented on `master` working tree 2026-08-27) | - | | WS08/WS15 own staging rollout of Redis+worker topology; WS27 extends (do not duplicate) the `ai_usage_ledger` | 2026-08-27 |
| WS09 API/edge | PARTIAL - core landed on `master` working tree 2026-08-27 (trusted hosts + boot guard, ProxyFix topology, non-spoofable rate-limit IP keying, CORS opt-in/fail-closed, request-ID + stable JSON errors incl. 400/405/500, Pydantic contracts on LLM/persistence routes, liveness/readiness/admin health split, nginx Permissions-Policy + staged HSTS + no-store, `docs/api-inventory.md`, tests in `api/tests/test_ws09_edge_security.py`) | - | - | Residual: remaining raw-JSON routes (admin internals, account edge cases) need contract sweep; TLS termination + HTTP→HTTPS redirect is operator-side (staged in nginx.conf); CSP Report-Only staging cycle pending | 2026-08-27 |
| WS10 Observability | PARTIAL (WS10-01/03/05 core implemented on `master` working tree 2026-08-27) | - | | WS10-02 OTel tracing + WS10-04 error aggregation + WS10-06/07 dashboards/alerts are deployment add-ons (WS15 staging); consumes WS09 request-id correlation | 2026-08-27 |
| WS06 Speaking/audio | BLOCKED by WS05/WS07 | | | | |
| WS12 Privacy/compliance | IN PROGRESS (policy pack + public legal pages + status register; engineering hooks VERIFIED integrated 2026-08-27: analytics 180d purge via maintenance job, audio ephemeral TTL, self-service deletion audited via user.delete audit event, export/delete scoped; outstanding: legal sign-off, minors policy decision, DSR SLA publication) | - | docs/privacy/ + docs/runbooks/INCIDENT_RESPONSE.md | legal review before public signup (WS12-03/04/05) | 2026-08-27 |
| WS11 CI/CD | PARTIAL (integrated 9f18d62: PG18 migration job + chained upgrade + alembic check (WS08), CodeQL, secret-scan, dependency audits (pip-audit/npm-audit) in security.yml, dependabot, brand-claim CI check, LICENSE posture; remaining: image/SBOM scan + staging deploy gates (WS15), Playwright E2E in CI) | 9f18d62 | | image scan + staging topology | 2026-08-27 |
| WS14 Validation | PARTIAL (test register + TV-07 k6 pack + TV-08 drill runbook + CodeQL + release-evidence template on `master` working tree 2026-08-27; TV-06/07/08 first executions pending staging) | - | docs/validation/TEST_REGISTER.md | staging needed for load/drill/restore evidence; TV-10 thresholds pre-registration (WS02) | 2026-08-27 |
| WS15 Deployment | BLOCKED by staging topology | | | | |
| WS16 Release gates | BLOCKED until candidate | | | | |
| WS27 AI token economy/task pooling | See ARUORA v2 table below (implemented 2026-08-27) | | | | |

## Status vocabulary
- `NOT STARTED`
- `READY`
- `IN PROGRESS`
- `PARTIAL`
- `BLOCKED`
- `REVIEW`
- `DONE`
- `ACCEPTED RISK`

## Integration rule
A workstream becomes `DONE` only after its branch is integrated and its acceptance tests pass on the integration branch. “Agent finished coding” is not `DONE`.

## ARUORA v2 workstreams

| WS | Scope | Status | Branch/PR | Evidence |
|---|---|---|---|---|
| WS20 | Product/domain contract | DONE (integrated `9f18d62`: canonical vocabulary + profile-extension map + Aura/Journey contracts in PRODUCT_DOMAIN_CONTRACT.md; readiness engine `readiness-v0` with route `GET /api/history/readiness` — deterministic, method-versioned, no percentage) | `9f18d62` | `api/tests/test_readiness.py` (8) |
| WS21 | Analytics/cohorts/WML | DONE (integrated `fde6b68`; WML reproducible, content-free envelope, server-owned cohorts, beacon allow-list, admin summary, 180d purge) | `fde6b68` | `api/tests/test_analytics.py` (20) |
| WS22 | UAT/Founding Beta operations | NOT_STARTED | | |
| WS23 | Brand/UI/Aura implementation | PARTIAL (tokens+AA remap, Plus Jakarta Sans, naming, Journey hierarchy, Aura copy registry, onboarding deadline step — `fde6b68`; remaining: WS13 routing/a11y sweep, full layout migration, brand QA checklist run) | `fde6b68` | web 74 tests + build |
| WS24 | Study Pool/community-safe preparation | DEFERRED_UNTIL_SIGNAL | | |
| WS25 | WhatsApp/re-engagement | DEFERRED_UNTIL_SIGNAL | | |
| WS26 | Human escalation/monetization boundary | DESIGN_ONLY | | |
| WS27 | AI usage ledger + shared task bank/replenishment | PARTIAL (Stage A in WS07; Stage B/C/E implemented on `master` working tree 2026-08-27) | - | Stage D scheduler/forecast + answer-key server-side grading deferred; `ai_usage_ledger` is shared with WS07 - do not duplicate | 2026-08-27 |
| WS28 | Auto-RAG Knowledge Pipeline | PARTIAL (Stage 1+2 DONE on `2fbd760`: registry/staged-atomic ingestion/canaries/hybrid retrieval/policy/cost-ledger; 20 §21 tests green; remaining: Stage 3 Aura-help UI, Stage 4 task-gen provenance wiring, Stage 5 pgvector+pg-rerank on production PG) | `2fbd760` | `api/tests/test_rag.py` (20) |

## Cohort evidence log

| Cohort | Build SHA | Users | P0/P1 | Key funnel | Decision | Notes |
|---|---|---:|---|---|---|---|
| internal_qa_01 | | | | | | |
| lecturer_uat_01 | | | | | | |
| linkedin_uat_01 | | | | | | |
| founding_beta_01 | | | | | | |

## Integration log (per 17 §Integration session)

### 2026-08-27 — Integration pass 1 (waves 1–3 partial)
- **Alembic:** single head `f1a2b3c4d5e6` (10 revisions, no branches) — verified via ScriptDirectory.
- **Conflicts resolved:**
  - `test_gate` heartbeat vs WS09 `GateHeartbeatIn`: layered contract documented — edge rejects `seconds > 7200` (422), route clamp still applies to in-range jumps (`2 × GATE_HEARTBEAT_SEC`). Test updated to assert both layers.
  - WS10 self-fixed logging-capture flakiness (env.py `disable_existing_loggers=False` + self-managed handler).
- **Checks executed (integration branch, working tree):**
  - API: `pytest -q` → **473 passed, 3 skipped, 0 failed** (77s).
  - Web: `tsc --noEmit` exit 0; `vitest` **29 files / 74 tests passed**; `vite build` ✓ 11.95s.
  - PostgreSQL-integration/E2E: NOT AVAILABLE locally (SQLite test tier) — required before WS16; tracked as staging gate.
- **Commits:** `fde6b68` (wave 1+2 integration), `2fbd760` (WS28 stage 1+2 + concurrent refresh).
- **Next-wave gate:** no MUST/P0 regression detected in integrated tree; WS03 session's email-verification rollout still in flight upstream — coordinate before Wave-4/5 evidence runs.

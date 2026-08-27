# 17 — Parallel Execution Guide

## Goal
Allow multiple Codex/LLM/developer sessions to work concurrently without creating migration conflicts or contradictory architectural changes.

## Golden rule
Parallelize by **file/domain ownership**, not by arbitrary task count. Database identity/ownership migrations are intentionally sequenced.

## Recommended workstreams
| ID | Document | Primary ownership | Can start after | Conflict risk |
|---|---|---|---|---|
| WS02 | `02_IELTS_SCORING_INTEGRITY.md` | domain scoring/tests | baseline | low |
| WS05 | `05_LLM_SECURITY_AND_CALIBRATION.md` | LLM gateway/prompts/schemas | baseline | low-medium |
| WS13 | `13_FRONTEND_ROUTING_ACCESSIBILITY.md` | frontend routing/UX | baseline | low |
| WS04 | `04_MULTI_USER_DATA_ISOLATION.md` | models/repos/ownership migration | baseline | high |
| WS03 | `03_IDENTITY_SESSION_SECURITY.md` | auth/session migration | WS04 ownership shape | high |
| WS08 | `08_DATABASE_MIGRATIONS_BACKUP_DR.md` | DB ops/compose/pool/migration CI hooks | WS04 schema direction | medium |
| WS07 | `07_JOBS_RATE_LIMIT_COST_CONTROL.md` | Redis/jobs/rate/quota | WS03 + WS04 | high |
| WS09 | `09_API_EDGE_SECURITY.md` | proxy/Flask edge | WS03 contract known | medium |
| WS10 | `10_OBSERVABILITY_SRE.md` | telemetry | WS07/WS09 shape | medium |
| WS06 | `06_SPEAKING_ASR_AUDIO_PIPELINE.md` | ASR/audio | WS05 + WS07 | medium-high |
| WS11 | `11_CI_CD_SUPPLY_CHAIN.md` | workflows | core changes stable enough | medium |
| WS12 | `12_PRIVACY_COMPLIANCE.md` | policy/data lifecycle | architecture known | low code conflict |
| WS14 | `14_TEST_VALIDATION_STRATEGY.md` | cross-system validation | main workstreams integrated | high integration |
| WS15 | `15_DEPLOYMENT_RUNBOOK.md` | release ops | staging topology | low |
| WS16 | `16_RELEASE_GATES.md` | acceptance | all | none |
| WS27 | `27_AI_TOKEN_ECONOMY_AND_TASK_POOLING.md` | task bank/exposure, AI usage ledger, generation/replenishment policy | WS04 + WS05; coordinate WS07/WS08 | high |

## ARUORA-aware additional workstreams

| Workstream | Scope | Conflict level |
|---|---|---|
| WS20 | Product/domain contract | Low; design first |
| WS21 | Cohort + analytics instrumentation | Medium; touches API/models/events |
| WS22 | UAT operations/release evidence | Low; depends on telemetry |
| WS23 | Brand tokens, hierarchy, Aura UI | Medium; frontend-heavy |
| WS24 | Study Pool opt-in only | Medium/high; start after WS04 ownership model |
| WS25 | WhatsApp | Deferred until opt-in demand; separate webhook/queue |
| WS26 | Human escalation | Design only until validated |
| WS27 | AI token economy + shared Task Pool | High; models/jobs/LLM usage; implement after ownership contract |

Recommended early parallelism after baseline:
- WS02 scoring;
- WS04 data isolation;
- WS05 LLM security;
- WS20 product contract;
- WS23 token/routing-compatible frontend groundwork.

WS21 should coordinate schema/event ownership with WS04. WS24 must not independently introduce relationship tables before WS04/WS12 rules are integrated.

## Execution waves
### Wave 0 — Baseline
One integration session:
- fetch latest branch;
- run test suites;
- create tag/branch point;
- ensure this document pack is committed.

### Wave 1 — Safe parallel foundation
Run in separate worktrees:
- Session A: WS02 scoring correctness.
- Session B: WS05 LLM role/schema hardening (avoid DB metadata migration until WS04 shape agreed; use interface/stub first).
- Session C: WS04 user data isolation/migration.
- Session D: WS20 map ARUORA product/domain requirements onto the current schema and API; design first, no competing migration.
- Session E: WS23 design-token migration and ARUORA hierarchy groundwork. If WS13 routing is also active, divide frontend files explicitly.

Integrate in order: WS02 → WS04 → WS05 → WS20 contract reconciliation → WS23/WS13 frontend reconciliation.

### Wave 2 — Identity + database + telemetry
After WS04 and WS20 contract reconciliation:
- Session F: WS03 identity/server sessions/CSRF/reset.
- Session G: WS08 PostgreSQL 18/DB ops/backup scaffolding that does not collide with WS03 migration; coordinate migration revision heads.
- Session H: WS21 implement cohort/acquisition/WML instrumentation against the accepted ownership/profile model.
- Session I: WS13 route/accessibility work that remains after WS23 integration.

If WS03/WS08/WS21 create Alembic revisions in parallel, expect branches. Prefer sequencing user-profile/event migrations or use an explicit Alembic merge revision after careful order review.

### Wave 3 — Runtime platform + AI economy
After WS03/WS08/WS21 and with WS05 integrated:
- Session J: WS07 Redis/jobs/rate/cost.
- Session K: WS09 edge/proxy/security headers.
- Session L: WS12 privacy/data-lifecycle implementation.
- Session M: WS27 Task Pool + usage ledger. Coordinate DB revision ownership with WS08 and queue/budget interfaces with WS07; do not independently fork LLM provider code owned by WS05.

Then WS10 observability after runtime/event shapes settle. WS22 UAT operations may prepare evidence templates at this point, but external cohorts do not start until release gates pass.

### Wave 4 — AI audio + delivery
- WS06 speaking/audio pipeline.
- WS11 expanded CI/CD.
- WS14 integration/load/security/calibration suites.

### Wave 5 — Staging/release/UAT
- WS15 deployment rehearsal.
- WS16 production go/no-go review.
- WS22 internal QA evidence.
- lecturer UAT only after internal QA exit criteria.
- LinkedIn market UAT only after lecturer fixes and cohort telemetry are stable.

WS24 Study Pool opt-in is allowed only after external UAT evidence supports it. WS25 and WS26 remain deferred until their product signals exist.

## Copy/paste session prompt template
Use this in a fresh session:

> Work on **WSXX** only for repository `junadwi009/ielts`. Read root `AGENTS.md`, `docs/production-readiness/README.md`, `00_MASTER_ROADMAP.md`, and the assigned WS document. Inspect the current branch before changes because the docs were based on a 2026-08-21 snapshot. Implement the smallest cohesive change satisfying the workstream acceptance criteria, add tests, do not modify another active workstream’s owned files unless unavoidable, and finish with the AGENTS.md completion report. Do not claim tests passed unless you ran them.

## Integration session prompt
> Integrate completed production-readiness branches in the documented order. Do not rewrite working implementations. Resolve migrations/API contracts explicitly, run the full API/web suites plus PostgreSQL integration/E2E checks available at this stage, and produce a conflict/risk report before merging the next wave.

## Worktree example
```bash
git fetch origin
git worktree add ../ielts-ws02 -b prod/ws02-scoring origin/master
git worktree add ../ielts-ws04 -b prod/ws04-data-isolation origin/master
git worktree add ../ielts-ws05 -b prod/ws05-llm-security origin/master
```

Adjust base branch if the repository moves to `main` or a dedicated production integration branch.

## Shared-file conflict rules
### `api/app/data/models.py`
Owner: WS04 first. WS03/WS07/WS06 add models only after WS04 is merged or via coordinated follow-up migration.

### `api/app/config.py`
Shared by WS03/WS07/WS09/WS10. Prefer additive named config sections and merge sequentially.

### `api/app/__init__.py`
Shared middleware integration point. Each workstream should minimize edits and expose helper initialization functions rather than accumulating inline logic.

### `api/app/services/llm.py`
Owner: WS05. Other workstreams call the gateway; do not fork provider logic.

### `.github/workflows/*`
Owner: WS11. Other workstreams add test scripts/config but let WS11 integrate them into required workflows.

### `docker-compose.prod.yml`
WS08 owns DB/runtime state corrections; WS07 may require Redis/worker additions. Sequence WS08 first, then WS07 updates the topology.

## Handoff requirements
Each branch writes/updates a short workstream log or PR description with:
- exact acceptance criteria completed;
- files and migrations;
- command outputs summary;
- unresolved issue IDs;
- whether next wave is unblocked.

## When parallelism should stop
Use one integration session when:
- two branches both rewrite the same model/migration;
- API schema changed on both sides;
- a security failure spans auth + data + proxy;
- staging deploy is being prepared.

More agents are not automatically faster when integration cost becomes the bottleneck.

### `GeneratedSet` / `GenUsage` evolution
Owner: WS27 after WS04 establishes ownership/deletion conventions. WS07 owns generic quota/job infrastructure; WS05 owns provider gateway. WS27 may add task-bank/exposure/usage-ledger models only through a coordinated Alembic revision. Do not let WS07 and WS27 each invent a separate AI usage table.


### `rag_*` schema / pgvector extension
WS28 owns RAG source/document/chunk/ingestion schemas and retrieval interfaces. Coordinate Alembic head with WS08 and `task_bank` provenance columns with WS27. Do not let separate sessions independently add vector extensions, embedding dimensions, or conflicting provenance schemas.

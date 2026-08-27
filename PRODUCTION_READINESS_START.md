# ARUORA IELTS Production Readiness v2.2 — Start Here

This v2.2 pack is designed to be extracted/merged into the root of `junadwi009/ielts`.

It combines:
- public multi-user production hardening;
- verified IELTS scoring/claim boundaries;
- ARUORA brand/product requirements;
- controlled UAT and Founding Beta telemetry;
- future-safe community/WhatsApp/human-help boundaries.

## Expected placement

```text
ielts/
├── AGENTS.md
├── PRODUCTION_READINESS_START.md
└── docs/
    ├── production-readiness/
    │   ├── README.md
    │   ├── 00_MASTER_ROADMAP.md
    │   ├── ...
    │   ├── 26_HUMAN_ESCALATION_AND_MONETIZATION_BOUNDARIES.md
    │   ├── 27_AI_TOKEN_ECONOMY_AND_TASK_POOLING.md
    │   └── 28_AUTO_RAG_KNOWLEDGE_PIPELINE.md
    ├── brand-source/
    │   ├── README.md
    │   ├── 01_BRAND_FOUNDATION.md
    │   └── tokens/aruora.tokens.json
    └── product-strategy-source/
        ├── README.md
        ├── 00_RECOMMENDED_STRATEGY.md
        └── ...
```

The source folders preserve the supplied ARUORA packs. The `production-readiness` folder converts them into implementation requirements.

## 1. Install and baseline the docs

```bash
git status
git add AGENTS.md PRODUCTION_READINESS_START.md docs
git commit -m "docs: integrate ARUORA public production program v2.2"
```

Do not blindly assume `master` if the integration branch has changed.

## 2. Baseline trigger — run before parallel implementation

Paste into one Codex/developer session:

> Establish the current baseline for the ARUORA IELTS production program. Read `AGENTS.md`, `PRODUCTION_READINESS_START.md`, `docs/production-readiness/README.md`, `00_MASTER_ROADMAP.md`, `20_ARUORA_PRODUCT_FOUNDATION.md`, and the current repository README/tests. Record current branch/SHA and CI state in `19_IMPLEMENTATION_TRACKER.md`. Run the available API and web test/build suites without making behavioral changes. Compare the current code with the 2026-08-21 reviewed baseline and explicitly report drift before implementation.

Typical checks:

```bash
git fetch origin
git status --short
git rev-parse HEAD

cd api
python -m pytest -q

cd ../web
npm ci
npx tsc --noEmit
npm test
npm run build
```

## 3. Recommended first wave

Use separate worktrees/sessions:

| Session | Workstream | Purpose |
|---|---|---|
| A | WS02 | IELTS scoring correctness and claim integrity |
| B | WS04 | User ownership, deletion, tenant isolation |
| C | WS05 | LLM trust boundary, output schema, calibration |
| D | WS20 | ARUORA product/domain contract mapping to current schema |
| E | WS23 | Brand token + UI hierarchy groundwork; coordinate routing with WS13 |

WS20 is design/schema planning first; it should not independently race WS04 on migrations.

## 4. Second wave — instrumentation before external UAT

After ownership/schema integration is stable:
- WS03 identity/session;
- WS08 database/migrations;
- WS13 route/accessibility integration;
- WS21 cohort + analytics + WML instrumentation;
- WS09 API/edge validation.

Before lecturer UAT, telemetry must distinguish `lecturer_uat_*` from other cohorts.

## 5. Runtime/AI wave

Then integrate:
- WS07 Redis/jobs/rate/cost controls;
- WS27 shared Task Pool, token/cost ledger, generation/replenishment economy;
- WS28 selective Auto-RAG knowledge pipeline, pgvector hybrid retrieval, source governance, and Task Pool grounding;
- WS06 audio/ASR evidence pipeline;
- WS10 observability;
- WS12 privacy/compliance;
- WS14 full validation.

## 6. Product rollout wave

Use `22_UAT_FOUNDING_BETA_RELEASE_PLAN.md`:

```text
Internal QA
→ Lecturer Controlled UAT
→ LinkedIn Market UAT
→ Free Founding Beta
→ Study Pool signal
→ Manual Study Pods only if validated
→ Community/Human Help later
```

Do not treat lecturer completion/retention as clean PMF evidence because participation is externally prompted.

## 7. Workstream trigger

> Implement **WSXX** for ARUORA IELTS. Read root `AGENTS.md`, `PRODUCTION_READINESS_START.md`, `docs/production-readiness/README.md`, `00_MASTER_ROADMAP.md`, the assigned workstream, and relevant source files under `docs/brand-source/` / `docs/product-strategy-source/`. Inspect current code before editing. Implement only the smallest cohesive change needed for acceptance criteria, including migrations/tests where required. Respect `17_PARALLEL_EXECUTION_GUIDE.md`. Update `19_IMPLEMENTATION_TRACKER.md` or provide the AGENTS handoff. Never claim a test passed unless executed.

## 8. UAT readiness trigger

Before each cohort:

> Audit this build for the next ARUORA UAT wave using `16_RELEASE_GATES.md` and `22_UAT_FOUNDING_BETA_RELEASE_PLAN.md`. Verify build SHA, environment, P0/P1 status, scoring claims, tenant isolation, auth/session behavior, rate/cost controls, telemetry/cohort attribution, privacy notice/consent, rollback path, and the exact product features enabled. Produce PASS/FAIL/BLOCKED evidence and do not expand the cohort on unresolved P0/P1 or MUST gates.

## 9. Integration trigger

> Integrate completed workstreams in the order documented in `17_PARALLEL_EXECUTION_GUIDE.md`. Re-read diffs and Alembic heads. Resolve schema/API conflicts explicitly. Run the strongest PostgreSQL/API/web/E2E checks available. Update `19_IMPLEMENTATION_TRACKER.md`. Stop the next wave if a MUST/P0 invariant regressed.

## 10. Public-release audit trigger

> Perform the public ARUORA IELTS release audit using `16_RELEASE_GATES.md`. Verify evidence—not implementation claims—for scoring correctness/calibration, Speaking evidence, BOLA/CSRF/session revocation, account deletion/export, backup/restore, migration rehearsal, cost/rate/backpressure, LLM adversarial tests, privacy/community opt-in behavior, observability/alerts, CI/supply-chain, ARUORA brand/claim integrity, accessibility, cohort telemetry, and rollback. Any unresolved MUST/P0 is NO-GO.

## 11. Stop conditions

Stop rollout/integration when:
- cross-user access is possible;
- ownership/deletion is ambiguous;
- migration risks unexpected data loss;
- auth/session dependency fails open;
- learner payload regains system-prompt privilege;
- LLM output bypasses server schema validation;
- official-score/pronunciation claims exceed evidence;
- rate/cost control is process-local in multi-worker public deployment;
- production secrets/default passwords are tolerated;
- backup/restore is assumed rather than demonstrated;
- analytics leaks essays/transcripts/audio/PII;
- Study Pool exposes users without explicit opt-in;
- an external UAT cohort cannot be attributed reliably;
- a P0/P1 issue remains open for the next exposure wave.

A feature-complete build is not production-ready, and a production-ready build is not automatically product-market validated.

## AI economy implementation trigger

After WS04 ownership/schema direction and WS05 LLM contracts are stable, use a dedicated session:

> Implement **WS27 AI Token Economy and Task Pooling**. Read `AGENTS.md`, `07_JOBS_RATE_LIMIT_COST_CONTROL.md`, `05_LLM_SECURITY_AND_CALIBRATION.md`, `08_DATABASE_MIGRATIONS_BACKUP_DR.md`, and `27_AI_TOKEN_ECONOMY_AND_TASK_POOLING.md`. Preserve current learner behavior while first adding provider usage accounting. Then evolve `GeneratedSet`/`GenUsage` through migrations rather than destructive replacement. Standard practice must become pool-first: Next/Try another selects a validated eligible pooled task; fresh generation is background replenishment or an explicit separately-metered custom feature. Coordinate Redis/job ownership with WS07 and migration ownership with WS04/WS08.

Do not launch external UAT until usage accounting can distinguish pool serves from billable inference and a global paid-inference kill switch has been tested.


## Auto-RAG implementation trigger

Run after WS05 LLM trust boundaries and WS08 database migration direction are stable; coordinate Task Pool integration with WS27 and queue ownership with WS07.

> Implement **WS28 Auto-RAG Knowledge Pipeline**. Read `AGENTS.md`, `01_TARGET_ARCHITECTURE.md`, `05_LLM_SECURITY_AND_CALIBRATION.md`, `07_JOBS_RATE_LIMIT_COST_CONTROL.md`, `08_DATABASE_MIGRATIONS_BACKUP_DR.md`, `12_PRIVACY_COMPLIANCE.md`, `27_AI_TOKEN_ECONOMY_AND_TASK_POOLING.md`, and `28_AUTO_RAG_KNOWLEDGE_PIPELINE.md`. Use PostgreSQL + pgvector + PostgreSQL full-text search as the initial implementation unless current infrastructure proves it unavailable. Build an allowlisted source registry, staged content-hash ingestion, structure-aware chunking, versioned embeddings, hybrid retrieval with metadata/authorization prefilters, provenance, and frozen retrieval tests. Do not add unrestricted crawling, do not embed private learner state, do not put dynamic RAG in calibrated scoring, and do not invoke RAG on normal pooled-task serving. Add provider/embedding/retrieval cost events to the WS27 ledger and preserve rollback to non-RAG core flows.

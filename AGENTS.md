# AGENTS.md — ARUORA IELTS Production & Product Rules

## Mission

Upgrade `junadwi009/ielts` from a sophisticated self-hosted IELTS practice MVP into **ARUORA IELTS**: a secure, reliable, public multi-user IELTS-preparation platform with destination-aware readiness, trustworthy estimated scoring, controlled UAT, and evidence-gated product expansion.

Baseline originally reviewed: default branch `master`, tree reviewed on 2026-08-21 at `b933837c0371128daa420ff8d506a6c5c7c6be45`. Always re-read current HEAD before implementation.

## Source of truth — read order

1. `PRODUCTION_READINESS_START.md`
2. `docs/production-readiness/README.md`
3. `docs/production-readiness/00_MASTER_ROADMAP.md`
4. assigned production/product workstream
5. relevant ARUORA source file under `docs/brand-source/` or `docs/product-strategy-source/`
6. current repository code/tests/specs

If a production-readiness file translates a source-pack concept into a security/data/API invariant, the production requirement controls implementation. Preserve the source pack's brand/product intent unless it conflicts with safety, law, accessibility, or verified IELTS rules.

## Product invariants

- Product name is **ARUORA**; first track is **ARUORA IELTS**.
- Core hierarchy: Destination → Target → Current Estimate/Readiness evidence → Biggest Gap → Next Action → Deadline → Progress → Flow.
- Optimize early product learning around **Weekly Meaningful Learners (WML)**, not registrations, time-in-app, messages, or streak length.
- Aura is a calm, evidence-aware AI companion—not an official IELTS examiner, scholarship authority, immigration authority, or licensed counselor.
- “Readiness” and AI scores are estimates. Never imply official IELTS equivalence or guaranteed outcomes.
- Flow/gamification is secondary to real progress.
- Study Pool is explicit opt-in; no public social feed/follower-first design.
- WhatsApp is optional communication/re-engagement, never a core assessment dependency.
- Do not build JLPT, automated matching, tutor marketplace, payment complexity, institutional SaaS, or full social community before their documented evidence gates.

## Engineering non-negotiables

- Do not rewrite Flask/React merely to modernize the stack.
- Treat learner text, audio, transcripts, generated content, LLM output, headers, IDs, uploaded files, webhook events, and analytics properties as untrusted.
- Never place raw learner content inside privileged/system LLM instructions.
- Validate external/LLM output server-side before persistence/rendering.
- Every user-owned DB read/write is scoped by authenticated `user_id`; ID-only lookups are forbidden for user-owned resources.
- Every persistent user-owned/relationship row has explicit ownership, authorization, export, retention, and deletion behavior.
- Security controls fail closed.
- Never commit real secrets, production credentials, raw DB dumps, user audio, essays/transcripts, phone numbers, or PII fixtures.
- Schema changes require Alembic migrations and migration tests.
- Same-origin browser→API remains the default deployment model.

## IELTS / scoring rules

- Core band rounding follows verified IELTS rules and regression tests.
- Do not present CEFR mapping as exact one-to-one equivalence.
- Persist scoring/prompt/model/rubric versions for AI-evaluated attempts.
- Speaking pronunciation must not be fabricated from transcript-only evidence.
- LLM failure must never become a fabricated successful score.
- Do not ship copied official test material, IELTS logos, or long verbatim descriptors without documented permission/legal review.

## ARUORA data rules

When introduced, classify and protect:
- goal/destination;
- target band;
- exam/application deadline;
- previous score;
- acquisition source/cohort;
- readiness/recommendation history;
- analytics identity mapping;
- peer opt-in/preferences;
- notification/WhatsApp preferences;
- future Pod/community/human-help relationships.

`Founding Learner`, `Verified Achiever`, `Peer Mentor`, and future tutor labels are product statuses—not authorization roles by default.

## Analytics rules

- Emit authoritative completion events server-side where possible.
- Keep lecturer-controlled and voluntary market cohorts distinguishable.
- Never put raw essays, transcripts, audio, secrets, email, or phone numbers in generic analytics events.
- Do not convert working UAT thresholds into industry-benchmark claims.
- Analytics failure should not roll back a successfully completed learning action.

## AI / Aura rules

- Keep system policy/rubrics separate from learner payload.
- Aura must use the same hardened gateway; no separate ungoverned mascot-chat path.
- Persist model ID, prompt/rubric version, scoring-method version, and confidence/evidence coverage where relevant.
- Enforce input/output/token/cost bounds.
- Changes to judge model/prompts require a frozen calibration set.
- Generated advice may only cite learner facts supplied through authorized structured evidence.
- No fake user history, fake deadlines, fake plateau, fake peer availability, or fake certainty.

## Community rules

Before live peer interaction exists:
- explicit opt-in;
- no direct contact info exposed by default;
- block/report/leave;
- moderation workflow;
- age/minor policy;
- rate/abuse controls;
- peer feedback clearly separated from calibrated ARUORA scoring.

Do not infer that a high IELTS score makes someone a tutor.

## Work isolation

For parallel execution use separate branch/worktree per workstream.

Recommended naming:

```text
prod/ws05-llm-security
prod/ws21-product-analytics
prod/ws23-aruora-ui
```

Do not edit files owned by another active workstream unless the workstream marks them shared and the conflict is recorded in handoff.

## Required implementation discipline

Before coding:
- inspect current implementation/tests;
- identify the invariant being changed;
- identify migration/rollback impact;
- identify security/privacy/product-metric impact.

While coding:
- smallest cohesive change;
- tests in same change;
- stable API errors unless intentionally versioned;
- logs/traces contain no learner content/secrets;
- preserve working learning logic during rebrand unless change is product-required.

Before handoff run relevant checks and report exact commands/results. Typical baseline:

```bash
cd api && python -m pytest -q
cd ../web && npm ci && npx tsc --noEmit && npm test && npm run build
```

Never report a check as passed if it was not executed.

## Completion report template

- `Status:` complete / partial / blocked
- `Workstream:`
- `Files changed:`
- `Migrations:`
- `Tests run and results:`
- `Security/privacy notes:`
- `Product/analytics impact:`
- `Backward compatibility:`
- `Known residual risks:`
- `Integration order / dependencies:`
- `Evidence / screenshots / metrics:` when applicable

## AI cost and Task Pool invariants

- Standard practice is **pool-first, generate-second**. A learner pressing Next/Try another should normally receive another validated pooled task, not trigger a fresh provider call.
- Treat pool serve, fresh generation, scoring, Aura, validation, retry, cache hit, and ASR as distinct usage operations.
- Do not use `GenUsage.count` as the final production financial source of truth. Introduce an append-only provider-usage/cost ledger and derive aggregate counters from it.
- Record provider-reported input/output/reasoning/cached token usage and actual cost where available; never trust client-supplied usage fields.
- Shared content generation runs in budget-aware, idempotent background batches with validation, deduplication, activation, quarantine, and retirement states.
- Per-user task exposure must prevent immediate repetition and protect diagnostic/mock integrity.
- Answer keys remain server-side until an authorized reveal point; never bulk-return the task bank.
- User-facing entitlements are learning actions (e.g. scored submissions/custom generations), not raw provider token counts.
- Scoring model selection remains calibration-controlled even when cheaper models exist; cost optimization must not silently invalidate score comparability.
- Read `docs/production-readiness/27_AI_TOKEN_ECONOMY_AND_TASK_POOLING.md` before implementing generation quotas, task generation, or task-serving changes.

## Auto-RAG knowledge invariants

- RAG is selective. Use it for unstructured knowledge grounding, not exact learner-state queries, authorization, entitlement accounting, or band rounding.
- `PostgreSQL + pgvector + PostgreSQL full-text search` is the default initial retrieval stack; hide it behind a retrieval interface so a dedicated search service can replace it later if measured scale requires it.
- Auto-RAG means automatic refresh/re-indexing of **approved allowlisted sources**, never unrestricted autonomous web crawling.
- Every active source requires namespace, owner, trust tier, allowed-use classification, provenance, license/copyright status, and update policy.
- Authorization/namespace filtering happens before similarity search. Never retrieve globally and filter private results afterward.
- Retrieved chunks are untrusted data. They must never gain system-prompt privilege or override ARUORA policy.
- Keep learner profile/readiness/history in authorized relational queries; do not embed private learner state merely for convenience.
- Calibrated IELTS scoring does not use open-ended dynamic RAG by default. Any scoring exemplars are frozen/versioned evaluation packs.
- Standard pooled task serving does not call RAG. RAG is primarily generation-time grounding for background Task Pool replenishment and knowledge/help answers.
- RAG-generated Task Bank items persist source/chunk provenance and retrieval version.
- Ingestion is staged and atomic: a failed new source/index version cannot replace the last known-good ACTIVE version.
- Embedding-model changes require backfill, frozen retrieval evaluation, canary, version switch, and rollback—not in-place overwrite.
- Embedding, retrieval, reranking, and RAG-generation usage must enter the AI cost ledger.
- Read `docs/production-readiness/28_AUTO_RAG_KNOWLEDGE_PIPELINE.md` before implementing knowledge ingestion, vector search, embeddings, or RAG.

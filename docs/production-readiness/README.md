# ARUORA IELTS — Public Production Readiness Program v2.2

## Purpose

This directory converts the existing `junadwi009/ielts` codebase into a public, multi-user production platform while preserving the product strategy and brand system defined by the ARUORA packs supplied on 2026-08-21.

The target is **ARUORA IELTS**, an independent IELTS-preparation product whose core promise is destination-aware readiness and next-best-action guidance. It must never imply that an AI estimate is an official IELTS result.

## Read order

### Every implementation session
1. `/AGENTS.md`
2. `/PRODUCTION_READINESS_START.md`
3. this file
4. `00_MASTER_ROADMAP.md`
5. the assigned workstream file
6. relevant source-of-truth product/brand files below
7. current repository implementation and tests

### Product and brand sources
- `../brand-source/README.md`
- `../brand-source/01_BRAND_FOUNDATION.md`
- `../brand-source/05_AURA_PERSONALITY_AND_VOICE.md`
- `../brand-source/06_UI_DESIGN_SYSTEM.md`
- `../brand-source/09_PRODUCT_BRAND_IMPLEMENTATION.md`
- `../brand-source/10_BRAND_GOVERNANCE_CHECKLIST.md`
- `../brand-source/tokens/aruora.tokens.json`
- `../product-strategy-source/00_RECOMMENDED_STRATEGY.md`
- `../product-strategy-source/05_UAT_AND_VALIDATION.md`
- `../product-strategy-source/12_ANALYTICS_AND_EXPERIMENTS.md`
- `../product-strategy-source/13_PRODUCT_ROADMAP.md`
- `../product-strategy-source/14_RISK_REGISTER.md`

The source packs are preserved in this bundle for provenance. Production-readiness files translate them into engineering requirements; they do not replace the original brand intent.

## Product invariants

ARUORA IELTS must optimize for:

1. **Destination** — why the learner needs IELTS.
2. **Target** — required band / outcome.
3. **Readiness** — explicitly an estimate, not an official score.
4. **Biggest gap** — what is holding the learner back.
5. **Next action** — what to do now.
6. **Deadline** — exam/application timing where known.
7. **Flow** — consistency, secondary to real learning progress.
8. **Belonging** — only after peer demand is validated.

Primary early North Star: **Weekly Meaningful Learners (WML)**, not raw registrations, streaks, messages, or time-in-app.

## Architecture stance

Keep the current Flask + React/Vite architecture unless a workstream proves a rewrite is required. Evolve it into a modular monolith with:

- PostgreSQL as system of record;
- Redis for shared rate limits, sessions/ephemeral state, and queues as appropriate;
- isolated workers for long-running LLM/ASR jobs;
- object storage for audio/media where retained;
- same-origin browser/API deployment;
- production observability and auditability;
- explicit cost and abuse controls.

Do **not** prematurely build:

- JLPT;
- a public social feed;
- follower counts;
- automated ML matching;
- an open tutor marketplace;
- a large reward economy;
- a fully conversational WhatsApp dependency;
- institutional SaaS features.

## Workstream map

### Core production hardening
`WS02–WS16` are the security, data, scoring, runtime, privacy, frontend, validation, CI/CD, and deployment workstreams.

### Product-aware production workstreams
- `WS20` — ARUORA product foundation/domain contract
- `WS21` — product telemetry, WML, cohorts, experiments
- `WS22` — controlled UAT → LinkedIn market UAT → Founding Beta
- `WS23` — ARUORA UI/design tokens/Aura integration
- `WS24` — Study Pool + future Study Pod/community safety architecture
- `WS25` — optional WhatsApp/re-engagement architecture
- `WS26` — human escalation and future monetization boundaries
- `WS27` — AI token economy, shared task pooling, generation accounting, anti-repeat, and replenishment
- `WS28` — selective Auto-RAG knowledge ingestion, hybrid retrieval, provenance, source governance, and RAG evaluation

## Delivery principle

Public production readiness and product-market validation are different gates.

A secure system with no voluntary learner return is not validated product-market demand.

A loved prototype with broken tenant isolation, misleading scoring, weak recovery, or uncontrolled AI cost is not production-ready.

Both must pass before broader release.

## AI economy stance

The standard content-delivery path is:

```text
validated shared task pool → randomized eligible task → learner attempt
```

not a fresh LLM generation per learner click. Fresh generation is primarily an asynchronous inventory-replenishment operation. User-specific scoring/Aura/audio remain separately metered. See `27_AI_TOKEN_ECONOMY_AND_TASK_POOLING.md`.


## Knowledge-layer stance

ARUORA uses a selective knowledge layer, not “RAG everywhere.” The default early-production implementation is PostgreSQL + pgvector + PostgreSQL full-text search behind a retrieval service. Auto-RAG refreshes only approved sources and is used primarily for Aura/help grounding and background Task Pool generation. Learner state remains relational and calibrated scoring remains pinned/versioned rather than dynamically retrieved. See `28_AUTO_RAG_KNOWLEDGE_PIPELINE.md`.

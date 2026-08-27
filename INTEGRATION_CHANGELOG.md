# ARUORA IELTS Public Production Pack — Integration Changelog

## Input packs

This version merges two inputs:

1. the existing IELTS public-production readiness pack;
2. `ARUORA_Strategy_Brand_Pack_v1.0.zip`, containing:
   - ARUORA Brand Identity v1.0;
   - ARUORA Market & Product Strategy v1.0.

The original ARUORA markdown/JSON files are preserved under `docs/brand-source/` and `docs/product-strategy-source/` so implementation agents can trace requirements back to source intent.

## Major changes from production pack v1

### 1. Product identity is now explicit
The target is **ARUORA IELTS**, not a generic public IELTS app.

The production program now protects these product invariants:
- Destination;
- Target;
- Current Estimate / Readiness evidence;
- Biggest Gap;
- Next Action;
- Deadline;
- Progress;
- Flow as secondary gamification.

### 2. Aura is treated as a governed AI surface
Aura is now explicitly bound to the hardened LLM gateway, evidence references, output validation, calibrated score claims, and non-authoritative language.

### 3. UAT strategy is part of release engineering
The pack distinguishes:
- Internal QA;
- Lecturer Controlled UAT;
- LinkedIn Market UAT;
- Free Founding Beta.

Cohort bias and evidence requirements are documented so lecturer participation is not accidentally reported as product-market fit.

### 4. Product telemetry is designed before UAT
The pack introduces:
- Weekly Meaningful Learners (WML);
- canonical acquisition sources;
- cohort IDs;
- minimum event taxonomy;
- privacy-safe analytics rules;
- experiment decision records.

### 5. Community is stage-gated
Only Study Pool opt-in is prepared initially. Study Pods, reputation, peer review, tutor supply, and marketplace features remain evidence-gated.

### 6. WhatsApp is optional
WhatsApp is modeled as an optional provider adapter for reminder/re-engagement, with consent, webhook security, cost observability, queueing, and no core assessment dependency.

### 7. Human escalation is future-safe without marketplace overbuild
The architecture can later support verified achievers, peer mentors, expert review, and tutors, but score alone never grants tutor authority and payments are outside the current release scope.

### 8. Brand implementation is connected to accessibility/security
Design tokens, Aura placement, visual hierarchy, reduced motion, critical score wording, and ARUORA brand governance now have production acceptance criteria.

### 9. Documentation defect fixed
The previous start guide referenced `docs/production-readiness/README.md` even though it did not exist. v2 adds that routing document.

## New production-readiness documents

- `20_ARUORA_PRODUCT_FOUNDATION.md`
- `21_PRODUCT_DATA_ANALYTICS_AND_EXPERIMENTS.md`
- `22_UAT_FOUNDING_BETA_RELEASE_PLAN.md`
- `23_BRAND_UI_AURA_IMPLEMENTATION.md`
- `24_STUDY_POOL_COMMUNITY_SAFETY_ARCHITECTURE.md`
- `25_WHATSAPP_REENGAGEMENT_ARCHITECTURE.md`
- `26_HUMAN_ESCALATION_AND_MONETIZATION_BOUNDARIES.md`

## Existing production documents updated

All existing operational markdowns except the generated manifest were updated where relevant. Key additions include:
- product-domain modules in target architecture;
- Readiness/score wording contract;
- product badge vs authorization-role separation;
- ownership for new profile/community data;
- Aura-specific LLM contract;
- Founding Beta AI-cost policy;
- staged schema sequencing;
- product event/WML observability;
- ARUORA UI and accessibility requirements;
- product funnel/UAT test suites;
- cohort-aware rollout and release gates;
- ARUORA-aware parallel execution.

## Explicitly still deferred

- JLPT;
- public social feed;
- follower system;
- automated/ML matching;
- full Study Pod product until manual validation;
- open tutor marketplace;
- payment stack;
- fully conversational WhatsApp assistant;
- institution dashboard;
- leaderboard/reward economy.

## v2.1 — AI token economy and Task Pool

Added `27_AI_TOKEN_ECONOMY_AND_TASK_POOLING.md` and integrated it across architecture, LLM, job/cost, database, observability, analytics, UAT, testing, release gates, parallel execution, and implementation tracking.

Key decisions:
- standard practice is pool-first, not fresh-generation-per-click;
- `GeneratedSet` becomes the migration seed for a validated shared task bank;
- `GenUsage(user/day/count)` is transitional and must not remain the only AI-cost record;
- introduce append-only provider usage ledger with actual model/token/cache/cost metadata;
- distinguish product entitlements from internal billing/token accounting;
- background generation uses inventory thresholds, budget envelopes, validation, duplicate control, and per-bucket idempotency;
- per-user task exposure prevents immediate repeat and protects diagnostic/mock integrity;
- OpenRouter usage/caching research was refreshed on 2026-08-21 and added to the reference register.


## v2.2 — Selective Auto-RAG knowledge layer

Added `28_AUTO_RAG_KNOWLEDGE_PIPELINE.md` and integrated RAG requirements across architecture, LLM security, jobs/cost, database, observability, privacy, testing, release gates, parallel execution, product evidence, and Task Pool economics.

Key decisions:
- RAG is selective rather than universal;
- initial stack is PostgreSQL + pgvector + PostgreSQL full-text search behind a retrieval service;
- Auto-RAG automatically refreshes approved/allowlisted sources, not arbitrary internet crawling;
- learner state remains exact relational data;
- calibrated scoring stays pinned/versioned and does not use open-ended dynamic RAG by default;
- RAG grounds background Task Pool generation, while pooled task serving remains inference-free;
- ingestion is versioned/staged with atomic activation and rollback;
- retrieval uses authorization/namespace prefilters, hybrid search, optional reranking, provenance, and frozen evaluation;
- embedding/retrieval/reranking costs enter the AI usage ledger;
- source license/copyright classification and near-copy rejection are explicit gates.

## Handoff — WS03 Identity/Session Security (integrated with concurrent WS07 edits)

WS03 landed in the same working tree as an in-flight WS07 (jobs/rate/cost) pass. Conflicts observed and resolved during integration:

- `api/app/__init__.py`: merged WS07 `JobService`/`ConcurrencyLimiter` wiring and the new `RateLimitService` before-request hook with the WS03 session/CSRF/email-gate blocks. `create_app` now wires: DI → WS07 jobs → WS03 sessions+CSRF (`SessionStore`, `test_client_class=CsrfAwareClient`) → WS03 `KV` abuse counters → rate limiting → passcode gate → email-verification gate.
- `api/app/config.py`: restored the lost `@property` decorator on `Config.provider_configured` (health endpoint returned 500 during the merge).
- `api/app/services/llm.py`: fixed a transient merge-corrupted string literal (`\`n`) that broke collection (subsequently also touched upstream).
- `api/tests/test_security_hardening.py` + `test_security_llm_auth.py`: ported stale `RateLimiter`/tuple `rule_for` assertions to the WS07 `InProcessBackend`/`Rule` API; password-policy cases moved to the WS03 15-char policy.
- `api/tests/test_admin.py`: destructive admin actions now require `POST /api/admin/reauth` (WS03-07) — tests updated accordingly.
- Migrations: both workstreams branched from `c8d21e4b7a30`; WS03's `b51f7aa3c9d0` was re-based onto WS07's `b7e4d2f19c08` to keep a single head.
- Shared test passwords were raised to the new 15-char minimum (`"correct horse battery staple"`) across the suite; repo-level password APIs still accept legacy hashes for existing users (transparent rehash on login).

WS03 residual notes for other workstreams:
- `Repository.session_factory` property added (additive, used by `SessionStore` to share the engine in the test DI path).
- `EMAIL_VERIFICATION_REQUIRED` (default 0) gates expensive LLM routes centrally in `create_app`; flip to 1 (with SMTP configured) before public launch or startup refuses.
- Admin MFA via `ADMIN_TOTP_SECRET` is optional per-deployment; GA release gate still requires mandatory MFA for all admin accounts.

## Handoff — WS06 Speaking/ASR/Audio Pipeline (integrated with WS07 jobs; WS09/WS10 landed concurrently)

WS06 was implemented on top of the WS07 job infrastructure and overlapped with concurrent WS09 (edge) and WS10 (observability) passes.

- `api/app/jobs/handlers.py` (WS07-owned): added the `transcribe` job handler (queue `asr`) — decode/transcribe + WS06-03 features + WS06-04 quality gate + immediate audio deletion. The existing `JOB_COST_CENTERS["transcribe"]` ledger mapping is reused unchanged.
- `api/app/session.py` (WS03-owned): `CsrfAwareClient` gained an `app` property for helpers that reach `app.config` via the client (WS09 tests expect it).
- Transcribe route contract change (WS06-02): uploads now enqueue on the `asr` queue and answer `202 {jobId}` when REDIS_URL/ASR_FORCE_QUEUE is set; dev (inline dispatcher) still returns the completed transcript with 200. Existing tests that fake `asr.transcribe` were updated to (a) accept `collect_segments` kwarg, (b) declare part mimetype `audio/webm` (the new MIME gate rejects `application/octet-stream`), and (c) include speech segments so the near-silence gate passes.
- WS06-05 is intentionally inert: `services/pronunciation.py` refuses to produce any pronunciation score until both `PRONUNCIATION_ESTIMATOR` and `PRONUNCIATION_CALIBRATION_VERSION` are configured against a frozen human-rated eval pack. Nothing else may call faster-whisper probabilities as "pronunciation".
- `docker-compose.prod.yml`: added a shared internal `ielts_audio` volume between `api` and `worker-infra` (ephemeral audio handoff, never publicly served) plus Celery time limits (`--time-limit=240 --soft-time-limit=180 --max-tasks-per-child=8`) on the ASR/mail worker (WS06-08).
- Known conflicts left to the owning workstreams: `test_ws09_edge_security.py` failures (expects `CORS_ORIGINS` config + its hostile-header test crashes inside werkzeug's own test client) and `test_ws10_observability.py` failures (scrubbing functions not yet implemented). Also `test_efficiency.py::test_reading_generates_until_pool_target_then_serves` conflicts with the WS07 duplicate-dedup design (identical stub payloads now hash-equal).

WS06 residual notes for other workstreams:
- `evaluate` accepts an optional `asrJobId`; only the caller's OWN succeeded `transcribe` job's server-computed features are attached (`metrics.audioFeatures`), and they are always stored separately from `metrics.llm` (WS06-06).
- Audio files live only in `ASR_AUDIO_DIR` (private volume), are deleted in the handler's `finally`, and a TTL janitor runs on every save. No audio URL exists anywhere in the API surface.

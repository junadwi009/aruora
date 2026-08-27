# 27 — AI Token Economy, Generation Accounting, and Shared Task Pooling

## Goal

Keep ARUORA useful under public multi-user traffic without allowing exercise generation to become an uncontrolled per-user LLM expense.

The preferred production model is:

```text
AI generates reusable content in controlled batches
        ↓
server validates + deduplicates + activates it
        ↓
content enters a level-aware Task Pool
        ↓
users receive randomized eligible tasks from the pool
        ↓
only user-specific work calls AI when it adds real value
        ↓
usage/cost is recorded in an append-only ledger
```

This workstream treats **content generation**, **content serving**, **scoring**, **Aura guidance**, and **ASR** as different economic operations. They must not share one ambiguous `count` field.

---

## 1. Why the current baseline is not enough

The reviewed repository already contains the **correct basic idea**, not a blank slate.

Current primitives include:

- `GeneratedSet(skill, band, set_index, payload, source, created_at)`
- `GenUsage(user_id, day, count)`
- `Repository.serve_set()` / `serve_any_set()` / `count_sets()` / `add_set()`
- `_gencap.serve_or_generate()` shared by Reading/Listening generation paths.

The current flow is effectively:

```text
if count(skill, band) >= POOL_TARGET:
    serve random stored set
else if user daily generation cap reached:
    serve from pool, then any-band fallback, else 429
else:
    synchronously call LLM
    store generated set
    increment that user's generation count
    return generated set
```

At the reviewed baseline, configuration defaults are `POOL_TARGET=7` per `(skill, band)` and `DAILY_GEN_CAP=20` per user/day. This is a strong MVP token-efficiency mechanism, but it should evolve rather than remain the production policy.

### Production problems in the current mechanism

1. **Shared inventory cost is charged to whichever learner arrives while a bucket is underfilled.** The generated item becomes a shared asset, but `GenUsage` increments that learner's personal daily count. Pool replenishment should be system-owned, not accidentally learner-owned.
2. **Generation is synchronous on the learner request path while the bucket is below target.** This adds latency and can create concurrent duplicate spend when traffic hits an underfilled bucket.
3. **Fixed `POOL_TARGET` freezes a bucket once full.** There is no lifecycle for refresh, retirement, quality drift, new topical diversity, or demand-based sizing.
4. **Random serving has no learner exposure history.** A learner can receive the same stored set repeatedly even while other unseen sets exist.
5. **The current repository selection loads matching rows and chooses in Python.** That is acceptable for seven items but not a scalable long-term selector.
6. **`serve_any_set(skill)` can cross the requested band/difficulty.** That may be tolerable as an explicit practice fallback in selected cases, but it is not safe as an invisible diagnostic/mock substitution.
7. **Generation enters the pool immediately.** Production needs lifecycle validation, quality flags, duplicate detection, and quarantine before activation.
8. **Client/request band must be validated or derived from authorized learner state.** An arbitrary new bucket must not become a way to force repeated pool misses/generation.
9. **`GenUsage.count` measures generations, not economic reality.** It cannot distinguish shared inventory creation from scoring, retry, cache hits, actual tokens, or actual provider cost.

Therefore WS27 is an **evolution of the existing Feature B pool-freeze design**, not a rewrite for its own sake.

`GenUsage.count` cannot answer:

- Was the action only a pool serve with zero LLM cost?
- Was it a fresh content-generation request?
- Was it a Writing/Speaking scoring call?
- Was it a retry caused by provider failure?
- Was it a provider response-cache hit?
- Which model/provider was actually used?
- How many input/output/reasoning/cached tokens were billed?
- What was the actual provider cost?
- Was the call initiated by a learner, admin, scheduled pool replenishment, calibration job, or UAT experiment?

`GeneratedSet` also cannot yet express:

- content quality state;
- validation state;
- generation batch and prompt/model provenance;
- exact task type/exam track;
- difficulty calibration;
- global exposure count;
- per-user exposure/repeat history;
- retirement/quarantine;
- duplicate/near-duplicate relationships;
- answer-key access boundaries.

Therefore **do not scale the existing daily count design as the final production accounting model**.

---

## 2. Core economic principle — pool-first, generate-second

For ordinary practice, a learner asking for a new task should normally trigger:

```text
request task
   ↓
select eligible unseen/recently-unseen item from Task Pool
   ↓
serve it
```

not:

```text
request task
   ↓
call LLM
   ↓
pay tokens
   ↓
serve one-off task
```

A learner clicking **Try another**, **Next question**, or equivalent should normally consume another pool item, not another generation call.

### Why this matters

If one AI generation creates a reusable task that can safely serve 20, 100, or 1,000 learners, generation cost is amortized across those serves. The expensive per-user AI calls can then be reserved for operations that truly depend on the learner's own response:

- Writing evaluation;
- Speaking evaluation;
- optional personalized Aura guidance;
- transcript/audio analysis;
- exceptional custom task creation when explicitly supported.

### Product rule

Do not expose implementation language such as “tokens remaining” to ordinary learners unless a commercial plan deliberately uses that concept. Product entitlement should use understandable limits such as evaluations, custom generations, or plan allowances. Internal finance uses tokens and actual cost.

---

## 3. Separate five kinds of usage

At minimum distinguish:

### A. Pool serve
A validated existing task is selected from the shared task bank.

Provider cost at serve time:

```text
~0 LLM tokens
```

It may still incur ordinary API/database/CDN cost.

### B. Pool replenishment generation
A background/admin job creates new reusable content.

This cost belongs to the shared content inventory, not directly to one learner.

### C. User-specific scoring
A learner submits Writing/Speaking content that must be assessed.

This is naturally per-user inference cost and should have stronger model/calibration controls.

### D. Aura/personalized reasoning
A learner requests or receives personalized guidance that cannot be produced from deterministic product logic alone.

Prefer deterministic recommendation logic where enough evidence exists; use LLM prose generation only when it materially improves the experience.

### E. ASR/audio computation
This may be local CPU/GPU cost or remote-provider cost. Track it separately from text-model tokens.

Do not combine these operations into a single daily generate counter.

---

## 4. Task Pool taxonomy

Do not use one undifferentiated pool for every IELTS feature.

Recommended `pool_kind` values:

```text
practice_adaptive
micro_drill
diagnostic
mock_form
```

### `practice_adaptive`
Normal skill practice. Reuse across learners is encouraged. Selection may adapt around the learner's demonstrated ability.

### `micro_drill`
Small focused exercises such as vocabulary, grammar, paraphrase, idea generation, pronunciation targets, or sub-skill remediation. High reuse is acceptable.

### `diagnostic`
Placement/readiness evidence. Forms must be controlled more carefully because repeated/leaked items can contaminate estimates.

### `mock_form`
Whole-test or test-like forms. Treat as higher-integrity inventory. Do not casually generate a new “mock test” on every click.

## Important IELTS validity boundary

Adaptive practice difficulty is a **pedagogical feature**, not a claim that official IELTS gives separate “Band 6 questions” and “Band 8 questions.”

For exam-simulation/diagnostic pools, preserve test-like difficulty and scoring assumptions rather than dynamically simplifying the task to the learner's current band.

---

## 5. Pool dimensions

A production task should carry structured dimensions rather than only `skill + band`.

Recommended dimensions:

```text
track              # IELTS initially
exam_variant       # academic / general_training / shared where valid
skill              # reading/listening/writing/speaking/etc.
task_type          # e.g. reading_mcq, writing_task2, speaking_part2
pool_kind          # practice_adaptive / diagnostic / mock_form / micro_drill
difficulty_bucket  # internal pedagogical bucket
cefr_hint           # optional approximate teaching hint
ielts_range_hint    # optional internal estimate range, never false precision
topic_family
content_version
language
```

For Writing Task 1 and other variant-specific content, do not mix Academic and General Training pools accidentally.

Do not force every dimension into a public UI label.

---

## 6. Proposed production data model

Names may be adapted to repository conventions, but preserve the concepts.

### 6.1 `task_bank`

Suggested fields:

```text
id UUID/bigint
track
exam_variant
skill
task_type
pool_kind
difficulty_bucket
cefr_hint nullable
ielts_min_hint nullable
ielts_max_hint nullable
topic_family nullable
payload JSONB
answer_key JSONB nullable       # never sent before authorized submission/review
explanation JSONB nullable
source                         # seed/manual/ai/imported
status                         # draft/validating/active/retiring/retired/quarantined
quality_score nullable
quality_flags JSONB
generation_batch_id nullable
prompt_version nullable
model_id nullable
provider nullable
content_hash
semantic_fingerprint nullable
created_at
activated_at nullable
retired_at nullable
```

### 6.2 `task_exposure`

Records which learner saw which task.

```text
id
user_id
task_id
served_at
completed_at nullable
attempt_id nullable
selection_context
result_summary JSONB nullable
```

Indexes should support:

```text
(user_id, task_id, served_at)
(task_id, served_at)
(user_id, served_at)
```

Do not store raw essay/audio again inside exposure rows.

### 6.3 `task_generation_batch`

```text
id
bucket_key
requested_count
accepted_count
rejected_count
status
source                       # scheduled/admin/recovery/calibration
model_requested
model_used
provider
prompt_version
schema_version
started_at
completed_at
failure_code nullable
input_tokens
output_tokens
reasoning_tokens
cached_input_tokens
cache_write_tokens
actual_cost_usd
```

The accepted/rejected distinction is important: generation cost must include failed-quality outputs so content economics are not understated.

### 6.4 `ai_usage_ledger`

Append-only source of truth for inference usage.

Suggested fields:

```text
id
request_id unique
job_id nullable
user_id nullable
operation                  # generate/validate/score/aura/asr_remote/etc.
request_source             # interactive/pool_replenishment/admin/calibration/uat
feature                    # writing/speaking/reading/listening/etc.
model_requested
model_used
provider
prompt_version nullable
rubric_version nullable
input_tokens
output_tokens
reasoning_tokens
cached_input_tokens
cache_write_tokens
provider_cache_status nullable
billable_request boolean
actual_cost_usd nullable
cost_source                # provider/calculated/unknown
status                     # succeeded/failed/cached/rejected
retry_of nullable
idempotency_key nullable
created_at
```

Do not store raw prompts/responses in this ledger.

### 6.5 Aggregate counters

Daily/monthly counters may be materialized for speed, but they are **derived**, not the financial source of truth.

Examples:

```text
pool_serves
fresh_generation_requests
fresh_generation_completed
scoring_requests
provider_billable_calls
provider_cache_hits
input_tokens
output_tokens
actual_cost_usd
```

The existing `GenUsage` can be retained temporarily as a compatibility projection while routes are migrated, then deprecated once all callers use the new policy service.

---

## 7. Entitlement counters are not billing counters

Do not make user entitlement depend directly on provider token count.

Why:

- models have different prices per token;
- cached tokens can have different prices;
- reasoning tokens may be billed differently;
- a retry can consume provider tokens without representing a new learner benefit;
- a pool serve gives real learner value with zero generation tokens;
- one batch generation can create multiple reusable tasks.

Maintain two layers:

### Product entitlement
Examples:

```text
practice pool serves
scored Writing submissions
scored Speaking submissions
custom task generations
Aura deep-feedback actions
```

### Internal cost accounting

```text
actual provider cost
tokens by model/provider
cache savings
ASR compute
shared generation amortization
```

A learner can therefore receive many randomized practice tasks without repeatedly consuming expensive “fresh generation” allowance.

---

## 8. Recommended learner-facing generation policy

### Standard practice

```text
pool only
```

No synchronous LLM generation unless the pool service cannot satisfy the request and the feature explicitly allows a fallback.

### “Try another”

```text
next eligible pool item
```

Do not equate this button with “regenerate via AI.”

### Personalized custom task
If introduced later, make it explicit and separately limited.

Examples:
- practice based on a specific learner weakness;
- a topic requested by learner;
- targeted remediation built from recent error patterns.

This path can consume a `custom_generation` entitlement.

### Scoring
Writing/Speaking scoring remains user-specific, but quotas and global budgets apply.

### Aura
Use deterministic recommendations first when possible. LLM should explain/coach, not recompute facts already available in structured learner evidence.

---

## 9. Selection algorithm — random, but not naive random

Pure `ORDER BY random()` is insufficient at scale and does not protect against repeats or overexposure.

Selection should be **eligible-filter + weighted random**.

### 9.1 Eligibility filter

Filter by:

```text
status = active
correct track/exam_variant
skill/task_type compatible
pool_kind compatible
difficulty allowed for current mode
not quarantined
not recently exposed to this user
not globally retired
answer-key policy valid
```

### 9.2 Preference order

Prefer:
1. never seen by this user;
2. not seen within the configured repeat-cooldown window;
3. under-exposed globally;
4. topic-diverse relative to recent learner history;
5. appropriate current difficulty/stretch mix;
6. high quality/confidence.

### 9.3 Example scoring concept

Do not hard-code these exact weights without testing, but the shape can be:

```text
selection_score =
  unseen_bonus
  + difficulty_fit
  + topic_diversity_bonus
  + quality_bonus
  - recent_exposure_penalty
  - global_overuse_penalty
```

Randomly select from the top eligible candidate window rather than always choosing the absolute top score. This preserves variety and avoids deterministic task sequences.

### 9.4 Anti-repeat horizon

Maintain a configurable no-repeat horizon per pool type.

Practice may allow eventual repeats for spaced reinforcement.
Diagnostic/mock items require stronger repeat controls and possibly form-level cooldown.

---

## 10. Adaptive practice mix

For **practice_adaptive** only, a starting pedagogical hypothesis may be:

```text
~60% current-fit difficulty
~30% stretch difficulty
~10% review/consolidation difficulty
```

This is a product hypothesis, not an IELTS rule. Tune it from completion, accuracy, abandonment, and learner feedback.

Do not apply the same adaptive mix to mock/diagnostic forms.

---

## 11. Pool sizing strategy

Do not pre-generate an arbitrarily huge library. Inventory should grow from measured demand.

For each bucket estimate:

```text
minimum_active = max(
  no_repeat_horizon_requirement,
  demand_exposure_requirement
)
```

One practical formulation:

```text
no_repeat_horizon_requirement =
  expected_tasks_per_user_during_cooldown × safety_factor

demand_exposure_requirement =
  projected_bucket_serves_7d / desired_global_reuse_per_item

target_active = minimum_active × inventory_buffer
```

All values are configurable and should be learned from UAT rather than published as industry standards.

### Example only

If a typical learner may consume 16 tasks in a bucket during the no-repeat horizon, a safety factor of 1.5 suggests 24 active items before repeat pressure becomes noticeable. If projected demand separately requires 20 items, the larger value wins. The replenishment target can then be set above the minimum.

Do not create thousands of tasks for a bucket with almost no active learners merely to make inventory numbers look large.

---

## 12. Replenishment controller

Run pool replenishment asynchronously.

### 12.1 Trigger

For each bucket:

```text
if active_ready_count < replenish_threshold:
    enqueue generation batch
```

Also forecast near-term demand so a bucket is replenished before it reaches zero.

### 12.2 Priority

When generation budget is constrained, prioritize:

1. buckets with active learners and imminent depletion;
2. high-value core IELTS practice;
3. diagnostic inventory needed for scheduled UAT;
4. lower-demand or experimental buckets last.

### 12.3 Locking

Use a distributed lock/idempotency key per bucket so multiple schedulers do not simultaneously replenish the same pool and double-spend.

Example conceptual key:

```text
pool-replenish:{bucket_key}:{generation_epoch}
```

### 12.4 Batch size

Do not assume one universal batch size.

A “generation unit” differs by skill:
- Reading may be one passage + question set;
- Listening may be one transcript/audio unit + questions;
- Writing may create several prompts cheaply;
- Speaking may create a topic/Part 1–3 family.

Start with small bounded batches and tune using actual acceptance rate, output-token cost, latency, and validation failure rate. A giant single response creates a large failure blast radius if schema or quality validation fails.

---

## 13. Generation quality pipeline

AI-generated content must not become active immediately.

Recommended lifecycle:

```text
DRAFT
  ↓
SCHEMA VALIDATION
  ↓
DETERMINISTIC QUALITY CHECKS
  ↓
DUPLICATE / NEAR-DUPLICATE CHECK
  ↓
OPTIONAL MODEL REVIEW FOR AMBIGUOUS CASES
  ↓
HUMAN SAMPLE / HIGH-INTEGRITY REVIEW WHERE REQUIRED
  ↓
ACTIVE
```

Possible terminal states:

```text
REJECTED
QUARANTINED
RETIRED
```

### Reading checks
- answer key is internally consistent;
- exactly one answer where the task requires one;
- question can be answered from passage evidence;
- no answer-key leakage;
- passage/question schema valid;
- no obvious copied/protected test material.

### Listening checks
- transcript/question/answer alignment;
- audio asset exists before activation where audio is required;
- no impossible timing/reference errors;
- answer key validated.

### Writing checks
- correct Academic/General Training task distinction;
- no “Band X question” wording that misrepresents IELTS;
- prompt is coherent and answerable;
- no hidden answer key concept.

### Speaking checks
- Part/type structure valid;
- safe/appropriate topic;
- no fabricated scoring target embedded in question.

High-integrity diagnostic/mock pools require stricter review than ordinary practice inventory.

---

## 14. Duplicate control without exploding token cost

Do not send the complete existing task library back to the LLM every time and ask it to avoid duplicates. That increases prompt tokens as the pool grows.

Prefer layered duplicate control:

1. canonical normalized content hash for exact duplicate;
2. cheap lexical fingerprint/SimHash/MinHash or equivalent for near duplicate;
3. optional embedding similarity once scale justifies it;
4. topic/constraint diversity at generation time;
5. post-generation rejection rather than ever-growing historical prompt context.

Store duplicate decisions so the same rejected content does not repeatedly enter validation.

---

## 15. Model routing strategy

Use different model policies by operation.

### Content generation
- cost-efficient model from an allowlist;
- strong structured-output performance;
- no need to use the expensive calibrated scoring model;
- batch/offline execution preferred.

### Content validation
- deterministic validation first;
- LLM validator only for checks deterministic code cannot answer;
- validator model may be cheaper than scorer if quality tests support it.

### Writing/Speaking scoring
- pin calibrated model + prompt/rubric version;
- do not silently auto-route across materially different models if that breaks calibration reproducibility;
- model changes require evaluation against frozen calibration data.

### Aura
- choose a model based on coaching quality/cost separately from score model;
- structured learner evidence remains source of truth.

Record both `model_requested` and `model_used` whenever routing can change the actual model.

---

## 16. Token management

### 16.1 Record actual usage, not only estimates

For OpenRouter, current Usage Accounting returns prompt/completion token counts, cost, reasoning tokens where applicable, and cached-token details in responses. Persist provider-reported usage when available.

A local tokenizer estimate may be used **before** submission for guardrails, but the provider response is the preferred billing truth.

### 16.2 Preflight token guard

Before provider call:
- enforce max learner input chars/words;
- enforce max conversation/history items;
- estimate request tokens when practical;
- reject/summarize/truncate only according to a documented feature policy;
- set explicit output-token ceiling.

Do not silently truncate learner Writing text being scored in a way that changes the result without telling the learner.

### 16.3 Keep static prompt prefixes stable

Long static rubrics/system instructions should remain stable and be placed before dynamic learner content. This improves compatibility with provider prompt caching where supported.

Dynamic content stays in the user/data portion of the request to preserve the security boundary.

### 16.4 Do not over-send history

Aura/roleplay should not resend unlimited full history. Use:
- bounded recent turns;
- structured learner state from database;
- explicit summaries when needed;
- no raw hidden history accumulation.

### 16.5 Output budgets

Generation and feedback prompts should request the shortest output that still serves the learning objective. Verbose hidden reasoning must not be requested merely because a model supports it.

---

## 17. Caching strategy

Caching is useful, but distinguish two different mechanisms.

### Provider prompt caching
Reuses repeated prompt prefixes while still producing a fresh response. This can reduce repeated input-token cost for stable rubrics/instructions on supported providers/models.

Good candidates:
- scoring rubric/system policy;
- stable generation schema/instructions;
- stable Aura policy prefix.

### OpenRouter response caching
OpenRouter currently offers a beta cache for **identical full requests**. A hit returns the previously cached response and reports zero billable usage.

Use only where identical replay is actually desirable, for example:
- idempotent retry of an exact deterministic operation;
- selected internal tests;
- a workflow step that must not be purchased twice.

Do **not** enable identical-response caching on a request whose purpose is “give me a different new task”; a cache hit would intentionally return the same content.

### Privacy constraint
OpenRouter documentation states account-level Zero Data Retention disables its response caching because response caching requires temporary storage. Provider prompt caching is a different mechanism and can have different ZDR compatibility.

Therefore:
- do not make response caching a required cost control for learner PII;
- use application idempotency regardless of provider cache;
- re-check provider policy before release.

---

## 18. Cost budgets and kill switches

Implement budgets at several levels.

### Global

```text
GLOBAL_DAILY_AI_COST_CAP
GLOBAL_MONTHLY_AI_COST_CAP
```

### Feature envelope

```text
POOL_GENERATION_BUDGET
SCORING_BUDGET
AURA_BUDGET
EXPERIMENT_BUDGET
```

### User/plan

```text
writing_scores_per_window
speaking_scores_per_window
custom_generations_per_window
aura_deep_actions_per_window
active_heavy_jobs
```

### Alert ladder

Example operational ladder:

```text
50% budget → informational
75% → warning
90% → high-severity warning / reduce nonessential replenishment
100% → hard stop for noncritical paid calls
```

Exact thresholds are configuration, not public promises.

When the global budget is close to exhaustion:
1. stop experimental generations;
2. delay low-priority pool replenishment;
3. preserve already-pooled practice;
4. preserve essential user-scoring according to product policy as long as budget permits;
5. surface controlled “temporarily unavailable” behavior instead of silently switching to an uncalibrated scorer.

---

## 19. Recommended initial budget strategy for UAT

Treat these as a starting operating hypothesis, not a permanent pricing model.

Allocate the AI budget into envelopes so one feature cannot consume everything. A reasonable first planning split can be:

```text
~55–65% learner scoring/evaluation
~15–25% shared pool generation + validation
~10–15% Aura/personalized feedback
~5–10% experiments/contingency
```

After the first UAT wave, replace assumptions with measured values:
- average cost per Writing evaluation;
- average cost per Speaking evaluation;
- task-generation acceptance rate;
- generation cost per activated task;
- average serves per activated task;
- pool hit rate;
- cost per WML;
- cost per activated learner;
- cache savings.

Do not optimize percentage allocation before these numbers exist.

---

## 20. Amortized task economics

For each generation batch:

```text
cost_per_accepted_task =
  total_generation_and_validation_cost
  / accepted_task_count
```

If five tasks are generated but only three pass validation, divide by three, not five.

For a task:

```text
amortized_generation_cost_per_serve =
  task_generation_cost / valid_serve_count
```

For a meaningful learning session:

```text
session_ai_cost ≈
  amortized_shared_content_cost
  + learner_scoring_cost
  + Aura_cost
  + remote_ASR_cost
```

This is more informative than “tokens per user” alone.

---

## 21. Metrics that must exist

### Inventory
- active tasks by bucket;
- validating/draft/rejected/quarantined tasks;
- time-to-replenish;
- pool depletion incidents.

### Serving
- pool hit rate;
- fallback rate;
- per-user repeat rate;
- global exposure distribution;
- task completion/abandonment by item;
- complaint/quality-flag rate.

### Generation quality
- generated → accepted rate;
- rejection reason;
- cost per accepted task;
- duplicate rejection rate;
- model/prompt version quality comparison.

### AI finance
- cost by operation;
- cost by model/provider;
- prompt/output/cached/reasoning tokens;
- provider-cache hit rate where enabled;
- retry cost;
- cost per WML;
- cost per activated learner/cohort.

### Learner value
Do not optimize pool hit rate at the expense of learning quality. Track learner outcome/feedback and task performance as well.

---

## 22. Pool depletion behavior

A depleted bucket must fail predictably.

Preferred order:

1. choose another eligible task from the same compatible bucket;
2. use a documented pedagogically safe adjacent practice bucket when the mode allows it;
3. enqueue replenishment in background;
4. return controlled limited-content behavior if no valid task exists.

Do not:
- synchronously spend unbounded tokens because one bucket is empty;
- serve a quarantined task;
- silently substitute a different exam variant;
- expose an answer key early;
- switch mock/diagnostic difficulty in a way that invalidates scoring.

---

## 23. Scraping and answer leakage controls

A shared task bank creates a scraping risk.

Controls:
- user-scoped/rate-limited serve endpoints;
- serve one task/set as needed, not dump full pool;
- keep answer keys server-side until authorized reveal;
- do not expose generation/admin metadata in learner API;
- monitor abnormal sequential fetching;
- limit anonymous access;
- rotate/retire compromised diagnostic/mock items;
- use content IDs that do not reveal inventory size/order.

Do not treat DRM as a substitute for legal/licensing review.

---

## 24. UAT strategy for task pooling

During internal QA and lecturer UAT, deliberately test inventory pressure.

Measure:
- how many tasks a motivated learner consumes per week;
- how often users request “another” task;
- repeat perception vs actual repeat count;
- which buckets deplete fastest;
- whether adaptive difficulty feels appropriate;
- generation acceptance/rejection rate;
- AI cost per meaningful learner;
- whether pooled content feels repetitive or generic.

For LinkedIn/founding beta, define before rollout:
- target pool-hit rate;
- acceptable recent-repeat rate;
- maximum tolerated depletion incidents;
- AI cost guardrail per activated learner/WML;
- inventory coverage by priority bucket.

Do not invent universal values; set product-specific gates from the controlled UAT baseline.

---

## 25. Immediate transition from the existing `serve_or_generate()` design

Before implementing the full target model, the safest behavioral evolution is:

```text
CURRENT
request → if pool under target → learner-triggered synchronous generation

TRANSITION
request → select existing eligible pool item
       → if inventory low, enqueue system-owned replenishment
       → return pooled task
```

For an empty bootstrap bucket, choose one explicit policy per mode:
- seed a minimum validated inventory before enabling the bucket; **preferred** for external UAT;
- allow one tightly idempotent system-owned bootstrap generation while the learner sees a controlled loading/job state;
- disable that bucket until inventory is ready.

Do not debit the learner's custom-generation entitlement merely because the platform itself needed inventory.

Replace the single fixed `POOL_TARGET` concept over time with at least:

```text
POOL_MIN_ACTIVE
POOL_TARGET_ACTIVE
POOL_MAX_GENERATION_PER_BATCH
POOL_REPEAT_COOLDOWN
POOL_REPLENISH_BUDGET
```

These may later become bucket-specific configuration derived from demand.

For the current `serve_any_set(skill)` fallback:
- remove it for diagnostic/mock paths;
- for adaptive practice, use only an explicitly compatible adjacent bucket;
- expose/record the actual difficulty served;
- never silently cross Academic/General Training task boundaries.

For current API compatibility, the route may keep `/generate` temporarily even when it serves a pool item, but new internal/domain naming should use `next_task`/`serve_task` so developers do not assume every request buys inference.

---

## 26. Recommended migration from current repository

### Stage A — preserve current behavior while adding accounting
1. Add append-only `ai_usage_ledger`.
2. Capture actual provider usage/model/cost on every LLM response.
3. Keep `GenUsage` compatibility behavior temporarily.
4. Add dashboards/alerts before changing user entitlement.

### Stage B — upgrade shared content model
1. Evolve `GeneratedSet` into or migrate it toward `task_bank` semantics.
2. Add explicit lifecycle/status/provenance/quality fields.
3. Add per-user `task_exposure`.
4. Move answer keys behind server-side authorization.

### Stage C — change practice serving
1. Standard practice routes select from pool.
2. “Try another” selects another eligible pooled task.
3. Add anti-repeat and diversity selection.
4. Do not synchronous-generate standard content on pool miss.

### Stage D — background replenishment
1. Add bucket inventory calculation.
2. Add threshold/forecast scheduler.
3. Add distributed lock/idempotency.
4. Add batch generation + validation pipeline.
5. Add generation-budget policy.

### Stage E — deprecate raw generation count
1. Replace route checks against one `GenUsage.count` with policy-service entitlements.
2. Keep historical migration/read compatibility as needed.
3. Remove table only after no route/report depends on it.

---

## 27. Suggested services/modules

Keep the modular monolith but create clear boundaries such as:

```text
app/services/ai_usage.py
app/services/ai_budget.py
app/services/task_pool.py
app/services/task_selection.py
app/services/task_generation.py
app/services/task_validation.py
```

Possible worker jobs:

```text
replenish_task_pool(bucket_key)
generate_task_batch(batch_id)
validate_task_batch(batch_id)
retire_low_quality_tasks()
rollup_ai_usage()
```

Do not put these business policies directly into Flask routes.

---

## 28. API contract direction

### Serve practice task

```text
POST /api/practice/next
```

Input contains requested skill/mode and safe context, not a demand to invoke AI.

Response includes:

```json
{
  "taskId": "opaque-id",
  "skill": "reading",
  "taskType": "...",
  "difficulty": "...",
  "payload": {},
  "source": "pool"
}
```

Do not expose model, prompt, answer key, generation cost, or internal quality notes.

### Submit task
Separate submission/evaluation endpoint so answer reveal and attempt persistence are controlled server-side.

### Custom generation
If a future endpoint exists, name and meter it explicitly rather than overloading `/next`.

---

## 29. Tests required

### Accounting
- one successful provider call creates exactly one usage ledger row;
- retries are linked and separately costed;
- pool serve does not create billable LLM usage;
- cached provider response records cache status/zero cost correctly when provider reports it;
- provider/model/token/cost fields survive asynchronous jobs;
- user cannot spoof cost/token values.

### Pool selection
- unseen item preferred;
- recently seen item excluded during cooldown;
- quarantined/retired item never served;
- Academic/General Training boundary enforced;
- answer key absent before allowed reveal;
- race between simultaneous requests does not repeatedly assign the same item when avoidable;
- empty bucket produces controlled fallback/replenishment signal.

### Replenishment
- only one replenishment job per bucket generation epoch;
- budget exhaustion prevents new paid generation;
- validation failure does not activate task;
- rejected tasks are counted in cost accounting;
- generated duplicate does not enter active pool;
- scheduler prioritization is deterministic/testable.

### Security
- task IDs cannot cross authorization boundaries for private attempts;
- pool endpoints cannot dump inventory;
- admin generation metadata requires admin authorization;
- raw prompts/responses never enter analytics/usage ledger.

### Product
- `Try another` can serve another task without an LLM call;
- pool repeat rate is measurable;
- WML is unaffected by whether content came from pool or fresh generation;
- learner analytics can distinguish pool serve from custom generation without storing content.

---

## 30. Release gates for this workstream

Before broader public beta:

- [ ] standard practice uses a shared validated pool by default;
- [ ] pool serve and fresh LLM generation are separate operations and counters;
- [ ] actual provider token/cost metadata is persisted where available;
- [ ] one global emergency AI-spend stop exists;
- [ ] per-feature/user quota policy exists;
- [ ] task lifecycle includes validation and quarantine;
- [ ] per-user task exposure prevents immediate repetition;
- [ ] answer keys are not bulk-exposed;
- [ ] background replenishment is idempotent and budget-aware;
- [ ] scoring model remains calibration-controlled and is not silently replaced to save cost;
- [ ] dashboards expose pool health + AI spend + cost per accepted task/WML;
- [ ] pool depletion behavior is tested.

---

## 31. Recommended production strategy summary

### What ARUORA should pay AI for

```text
Generate reusable inventory occasionally
Score learner-specific work when needed
Coach with Aura when deterministic guidance is insufficient
Process learner audio when required
```

### What ARUORA should not pay AI for repeatedly

```text
The same style of Reading question for every learner
The same Writing prompt family for every click
A new Speaking topic every time a user presses Next
Deterministic progress summaries already computable from stored evidence
Duplicate calls caused by retry/double-click
```

### Target architecture

```text
                     ┌─────────────────────────────┐
                     │ AI Generation Worker        │
                     │ budget + batch + validation │
                     └──────────────┬──────────────┘
                                    │
                                    ▼
┌─────────────┐             ┌───────────────┐
│ Learner     │ ──next────▶ │ Shared Task   │
│             │             │ Pool / Bank   │
└──────┬──────┘             └───────┬───────┘
       │                            │
       │ submit response            │ task provenance
       ▼                            ▼
┌─────────────┐             ┌───────────────┐
│ Score/Aura  │ ──────────▶ │ AI Usage      │
│ Worker      │             │ Ledger        │
└─────────────┘             └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ Cost/Pool/SRE │
                            │ Dashboards    │
                            └───────────────┘
```

The result is a system in which **learning inventory scales mostly with database delivery, while expensive AI inference scales only with personalized value**.

---

## 32. Current external-provider notes — verify again before implementation

As researched on 2026-08-21:

- OpenRouter Usage Accounting documentation states responses include detailed usage such as prompt/completion tokens, cost, reasoning tokens where applicable, and cached-token details.
- OpenRouter documents provider prompt caching and exposes cached-token/cache-write information where supported.
- OpenRouter Response Caching is currently documented as a beta feature for identical requests; cache hits have zero billable usage, but account-level ZDR disables this response cache.
- OpenRouter provider/data-retention behavior varies by upstream provider, so routing privacy policy must remain explicit.

Primary references are registered in `18_RESEARCH_REFERENCES.md`.

Re-verify these capabilities and privacy terms immediately before production implementation because provider behavior and pricing can change.


## 33. Auto-RAG integration

WS28 adds a knowledge-grounding layer to replenishment without changing the core pool-first economy.

```text
Inventory shortage
→ generation batch
→ approved RAG context pack
→ generate original task
→ validate factual consistency + originality
→ Task Bank
→ serve many times without RAG/LLM
```

Add ledger operation categories for embedding ingestion/query, reranking, RAG task generation, and RAG validation. A normal pool serve must not produce those events. Persist `rag_context_pack_id`/retrieval version/source provenance on generated tasks or generation batches. Dynamic RAG remains excluded from calibrated scoring unless a separately versioned evaluation design is validated. See `28_AUTO_RAG_KNOWLEDGE_PIPELINE.md`.

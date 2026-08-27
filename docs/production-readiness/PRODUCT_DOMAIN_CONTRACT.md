# WS20 — ARUORA Product/Domain Contract

Design-first deliverable (per 17 §Wave 1, Session D): the canonical mapping
from ARUORA product strategy (docs/product-strategy-source/) onto the current
schema and API. Design only — no competing migrations.

## 1. Canonical vocabulary (single source of truth)

| Product term | Engineering object | Current status |
|---|---|---|
| **Aura** | Persona layer over `LlmGateway` (`app/rag` context + `aura.ts` approved copy). Never a security principal. | copy registry live; chat surface deferred |
| **Ask Aura** | Future route reusing the hardened gateway + `help_answer` RAG namespace set | deferred until Aura ships |
| **Destination** | `user_profile.goal` (`work \| study_abroad \| other`) + optional future free-text/country field | live (Home Journey strip) |
| **Readiness** | `GET /api/history/readiness` — deterministic `app/domain/readiness.py`, method-versioned | live (readiness-v0) |
| **Flow** | `statsActivity` streak counters — secondary metric, never a goal | live (label "day Flow") |
| **Journey** | Program/Milestones tables + guided lesson cache | live; engine_version per 20 §recommendation when automation grows |
| **Study Pool** | Explicit opt-in (future `peer_opt_in` default false) | deferred (WS24, evidence-gated) |
| **Study Pod** | Not built until manual validation | deferred |
| **Founding Learner / Verified Achiever / Peer Mentor** | Metadata/badge only — never an authorization role | n/a |

Security/auth/access-control labels stay technically precise; brand terms
never rename a functional control.

## 2. Profile extension map (progressive, privacy-classified)

| Field | Class | Storage today | Notes |
|---|---|---|---|
| goal_type | personal | `goal` (enum) | live |
| destination (country/institution) | personal | **missing** — add later as optional `destination` text | only when a feature needs it |
| target_band | personal | `target_band` | live |
| exam_date / deadline | personal | `exam_date` | live (month-normalized) |
| previous_score | personal | **missing** — optional, source-labeled when added | |
| study_capacity | personal | **missing** — optional categorical | |
| acquisition_source / cohort_id | analytics (WS21) | live, server-validated | |
| peer_opt_in / peer_skill_interest / peer_availability | relationship | **missing** — default false, WS24 gate | |

Rules honored: nothing beyond goal/target is required at signup; registration
attaches to the draft-profile; all additions join export/delete governance
(DATA_OWNERSHIP_INVENTORY.md).

## 3. Readiness contract (implemented)

`GET /api/history/readiness` returns exactly the 20 §Readiness shape:
`method` (readiness-v0) · `generatedAt` · `targetBand`/`skillTargets` ·
`currentEstimate` (officially rounded mean of latest per-skill practice
estimates; `null` with zero evidence) · `gap`/`prioritySkill` ·
`evidenceCoverage` (assessed/total/complete/missing) · `estimateBasis` ·
`disclaimer`.

**No percentage field exists** (tested). Percentage readiness may only be
introduced as a documented product heuristic with its own method version.

## 4. Journey recommendation contract

Today's recommendation currently derives deterministically (weakest assessed
skill on Home; guided-session focus from `pick_focus`). When recommendations
become richer records, each must carry: `user_id`, `recommendation_type`,
`reason_code`, `evidence_snapshot`, `target_snapshot`, `generated_at`,
`expires_at|recompute policy`, `engine_version`. LLM text may EXPLAIN a
server-side recommendation; deterministic policy owns hard constraints.

## 5. Aura contract

As per 20 §Aura + 05 §Aura contract: calm/concise/evidence-aware; Observation
→ evidence → next action → confidence/limitation; no examiner/official/
guarantee claims (regex-guarded in `web/src/lib/aura.ts`); learner evidence
(PostgreSQL) and knowledge context (WS28 RAG, `help_answer`/`aura_advice`
namespace sets) stay separate inputs with provenance; never infer learner
facts from knowledge chunks.

## 6. Cross-track compatibility

Global (account, consent, acquisition, community identity, communication
preferences) is stored track-agnostic. IELTS-specific artifacts (band rules,
rubrics, question types, scoring calibration) live under `ielts_*` naming
and the WS02/WS28 versioned packs. No curriculum generalization before a
future track earns its own discovery workstream.

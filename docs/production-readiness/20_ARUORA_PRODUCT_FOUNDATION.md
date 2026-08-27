# 20 — ARUORA Product Foundation and Domain Contract

## Goal

Translate the ARUORA brand/market strategy into stable product-domain requirements without forcing speculative community or monetization features into the first public release.

## Product thesis

ARUORA IELTS evolves from a generic AI IELTS coach into an **IELTS Readiness Network**.

Core learner loop:

```text
Where am I?
    ↓
What is my destination and target?
    ↓
What is the gap?
    ↓
What should I do today?
    ↓
Did that action improve readiness?
    ↓
When self-study is insufficient, who can help?
```

## Canonical vocabulary

| Generic concept | Product term | Engineering note |
|---|---|---|
| AI assistant | Aura | Persona/presentation layer; never a security principal |
| AI chat | Ask Aura | Uses same hardened LLM gateway |
| learning goal | Destination | Store machine-readable goal + optional free text |
| progress estimate | Readiness | Must include method/version/confidence |
| streak | Flow | Secondary product metric only |
| learning path | Journey | Version plan generation |
| matching candidate pool | Study Pool | Explicit opt-in required |
| small learner group | Study Pod | Do not build until manual validation |
| early beta user | Founding Learner | Cohort/status, not authorization role |
| successful helper | Verified Achiever / Peer Mentor | Future role with verification process |

Product terminology must never obscure a functional control. Security/auth/access-control labels stay technically precise.

## Minimum profile extension

Design migrations so the current user profile can later represent:

```text
goal_type          scholarship | study | work | retake | migration | other
destination        country/institution/context, optional
target_band        decimal or structured skill targets
exam_date          optional exact date
deadline           optional product deadline
previous_score     optional, source-labeled
study_capacity     optional categorical/minutes-per-week
acquisition_source controlled enum/string
cohort_id           controlled cohort identifier
peer_opt_in         false by default
peer_skill_interest optional
peer_availability   optional structured value
```

Rules:
- do not require every field at signup;
- progressive profiling is preferred;
- `peer_opt_in` must default false;
- `Founding Learner` is metadata/badge, never an access-control shortcut;
- destination/deadline are personal profile data and follow privacy/export/delete policies.

## Readiness contract

`Readiness` is not a second IELTS score.

Every readiness output must document:
- source inputs;
- scoring/heuristic version;
- last updated time;
- confidence/coverage;
- whether all four IELTS skills were directly assessed;
- target used for gap calculation.

A percentage such as `68% readiness` is prohibited until a reproducible formula is implemented and validated. Until then use clearer constructs such as:

```text
Current estimate: 6.0
Target: 7.0
Gap: 1.0 band
Priority: Writing
Evidence coverage: 3/4 skills recently assessed
```

If a percentage is introduced later, treat it as a product heuristic, not a scientific probability.

## Journey recommendation contract

Today's recommendation must be explainable from learner state.

Minimum recommendation record:
- `user_id`
- `recommendation_type`
- `reason_code`
- `evidence_snapshot`
- `target_snapshot`
- `generated_at`
- `expires_at` or recomputation policy
- `engine_version`

Never let an LLM silently determine an irreversible user state. LLM text may explain a server-side recommendation; deterministic policy should own hard constraints and safety rules.

## Aura contract

Aura is a product companion, not an examiner, scholarship authority, immigration authority, counselor, or tutor-of-record.

Aura voice:
- calm;
- concise;
- specific;
- contextual;
- non-patronizing;
- evidence-aware;
- no guilt/streak shame;
- no fake certainty;
- no guaranteed band or scholarship outcome.

For AI-generated learner-facing advice, prefer:

```text
Observation → evidence → next action → confidence/limitation
```

## Cross-track future compatibility

ARUORA may later support other language/exam tracks. Avoid hardcoding global account/community infrastructure to IELTS-only concepts.

Good split:
- global: account, consent, destination, acquisition, community identity, communication preferences;
- track-specific: IELTS attempts, band rules, rubrics, question types, scoring calibration.

Do not generalize curriculum prematurely. Future JLPT support must earn its own discovery/validity workstream.

## Acceptance criteria

- product terms have one canonical definition;
- profile additions are progressive and privacy-classified;
- readiness cannot be mistaken for an official result;
- Aura behavior is constrained by the same LLM safety/output contracts as other AI surfaces;
- architecture stays compatible with future tracks without weakening IELTS-specific correctness;
- no speculative social/tutor functionality is required for initial public beta.


## Knowledge context contract

ARUORA distinguishes **learner evidence** from **knowledge context**. Learner evidence (targets, scores, attempts, deadline, activity) is exact structured data from PostgreSQL. Knowledge context (pedagogy, help, factual reference, approved IELTS rules) may come through WS28 RAG. Aura may combine them, but must preserve provenance and never infer learner facts from semantically similar knowledge chunks.

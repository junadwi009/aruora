# 22 — UAT, Founding Beta, and Product Validation Release Plan

## Goal

Stage exposure so security/correctness risk, usability validation, and market-demand validation are not mixed into one launch.

## Wave 0 — Internal QA

Target: 2–5 trusted users.

Must exercise:
- registration/login/logout/recovery;
- onboarding/profile;
- placement and result;
- program/Journey;
- Reading/Listening/Writing/Speaking;
- microphone/audio failure paths;
- progress/history;
- settings/export/delete where implemented;
- mobile/desktop;
- LLM/provider failure;
- rate/quota behavior;
- session recovery.

Exit:
- P0 = 0;
- P1 = 0;
- no cross-user access;
- no misleading official-score claim;
- scoring-rounding regression suite green;
- production telemetry can identify failures.

## Wave 1 — Lecturer Controlled UAT

Recommended: 20–50 students plus separate lecturer/expert review.

Purpose:
- usability;
- placement completion;
- learning-flow comprehension;
- feedback usefulness;
- pedagogical reasonableness;
- bug discovery.

Student and lecturer questionnaires must be separate.

Bias rule: participation may be prompted by the lecturer. Do not present this cohort's retention as proof of market demand.

## Wave 2 — LinkedIn Market UAT

Recommended: 30–50 qualified voluntary users.

Qualification should favor people with a real IELTS goal:
- scholarship;
- overseas study;
- retake/plateau;
- career/migration requirement where relevant.

Measure:
- voluntary signup;
- onboarding/placement completion;
- first meaningful session;
- D1/D7 meaningful return;
- perceived usefulness of result/plan;
- peer-practice interest;
- failure/churn reasons.

Working signals from the supplied strategy pack—not industry benchmarks:

| Metric | Initial signal |
|---|---:|
| Registration completion | >80% |
| Placement started | >75% of registered |
| Placement completed | >60% |
| First meaningful session | >45% |
| Placement perceived useful | >70% of respondents |
| Plan perceived relevant | >70% of respondents |
| D1 meaningful return | >35–40% |
| D7 meaningful return | >20–25% |
| Peer-practice interest | >40% |
| P0/P1 bugs | 0 |

These thresholds are hypotheses. Qualitative evidence and sample quality matter.

## Wave 3 — Free Founding Beta

Target: roughly 100–300 qualified/active learners only after Wave 2 evidence is acceptable.

Public framing:

> Free during Founding Beta

Do not promise free forever.

Required controls even when free:
- per-user generation quota;
- provider/cost budget;
- rate limiting;
- abuse controls;
- cached/pre-generated content where pedagogically appropriate;
- kill switch for expensive AI paths.

Add only validated product scaffolding:
- Founding Learner status/badge;
- progressive destination/deadline profile;
- richer readiness/gap display;
- Study Pool opt-in;
- referral/acquisition tracking.

Do not build a full community feed or tutor marketplace.

## Interview sampling

For an initial 30–50 market cohort, deliberately include:
- heavy users;
- typical users;
- low-activity users;
- churned users;
- high-intent scholarship/retaker users.

Ask about behavior:
- Why do you need IELTS?
- What did you use before?
- Where do you get stuck?
- What do you do when stuck?
- What made you return or stop?
- When is human feedback worth paying for?

Avoid feature-wishlist interviews as primary evidence.

## Evidence required to expand exposure

Before moving from controlled UAT to broader beta:
1. core production MUST gates pass for the actual deployment profile;
2. telemetry is reliable;
3. scoring/AI claims are truthful;
4. voluntary cohort shows meaningful return;
5. user-support/incident path exists;
6. backup and rollback have been demonstrated;
7. cost envelope is understood;
8. privacy notice/consent matches actual collection.

If retention is weak, do not add community merely to hide the problem.

## Rollback / freeze rule

Any P0 security/privacy/scoring issue freezes cohort expansion. Existing users may remain only if the incident owner explicitly confirms safe degraded operation.

## AI cost and Task Pool evidence

Before each cohort expansion record:
- pool hit/fallback/depletion rate by priority skill bucket;
- median/upper-percentile tasks consumed per active learner;
- recent-repeat rate and qualitative repetition complaints;
- shared generation cost per activated task;
- accepted/rejected generation ratio;
- Writing/Speaking evaluation cost distributions;
- total AI cost per WML and activated learner;
- any hard-budget intervention.

Use controlled UAT to set a product-specific inventory target. Do not pre-generate a huge library based on vanity inventory count.

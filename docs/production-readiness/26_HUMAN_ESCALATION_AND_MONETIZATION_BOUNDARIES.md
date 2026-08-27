# 26 — Human Escalation and Future Monetization Boundaries

## Goal

Design today's AI/self-study system so high-intent or plateau learners can later escalate to humans without prematurely shipping a tutor marketplace.

## Escalation principle

```text
self-study / AI
→ structured peer help (if validated)
→ verified mentor / expert feedback
→ tutor session
```

Escalation should be based on evidence such as:
- repeated plateau across comparable attempts;
- deadline risk;
- user explicitly asks for human review;
- low confidence/coverage in automated assessment;
- complex feedback where AI is inappropriate.

Never manipulate anxiety to sell help.

## Supply ladder

Do not equate test score with teaching ability.

Future ladder:

```text
Learner
→ Verified Achiever
→ Peer Contributor
→ Peer Mentor
→ Tutor Candidate
→ Teaching Calibration
→ ARUORA Tutor
→ Senior Tutor
```

Each promotion requires documented criteria. Authorization roles for tutor/admin functions must remain separate from marketing badges.

## Human-feedback product hypotheses

Potential later paid value:
- Writing expert review;
- Speaking review;
- targeted diagnostic session;
- intensive 30/60/90-day cohort;
- tutor sessions.

These are hypotheses, not release requirements.

## Marketplace boundary

Do not build marketplace payments/booking/take-rate logic until evidence exists for:
- user willingness to book;
- reliable supply;
- repeat sessions;
- clear platform value;
- manageable support/dispute burden.

If a payment system is later added, create a dedicated financial/payment security workstream rather than inserting payment fields into ordinary user tables ad hoc.

## Tutor privacy/safety

Future human-help design must cover:
- identity/credential verification appropriate to claims;
- user/tutor block/report;
- session audit metadata;
- payout/tax/legal review where applicable;
- minors policy;
- dispute/refund policy;
- content/session retention;
- off-platform contact boundaries.

## Monetization integrity

During UAT/early Founding Beta optimize:
- activation;
- meaningful learning;
- retention;
- score-feedback trust;
- user density;
- first-party behavioral evidence.

Do not optimize revenue before core learning value is validated.

## Acceptance criteria for current production program

- schema/architecture does not assume every helper is a tutor;
- no high-score-to-tutor auto-promotion;
- product has a safe future escalation boundary;
- monetization does not block Founding Beta core flows;
- no marketplace/payment complexity is introduced without a separate validated workstream.

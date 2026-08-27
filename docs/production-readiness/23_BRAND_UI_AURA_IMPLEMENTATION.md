# 23 — ARUORA Brand, UI System, and Aura Implementation

## Goal

Migrate the existing IELTS Coach frontend into ARUORA without rewriting functioning learning logic for cosmetic reasons.

## Brand hierarchy

Product: **ARUORA** / track: **ARUORA IELTS**.

Parent endorsement may use:

```text
aruora
by ARUSTUDIO
```

`by ARUSTUDIO` stays secondary. Do not make the normal product surface look like an equal co-brand collaboration.

## UI information hierarchy

Home priority:
1. Destination
2. Target
3. Current estimate / Readiness evidence
4. Today's recommendation
5. Biggest gap / weakest skill
6. Progress trend
7. Deadline
8. Flow
9. Community/Study Pod only when available

The first screen should answer: **Where am I, what matters, and what should I do now?**

## Design tokens

Use `../brand-source/tokens/aruora.tokens.json` as the initial token source.

Core palette:
- Aura Cream `#F4F0E9`
- Midnight Ink `#19172B`
- Ink `#282631`
- Aura Violet `#7568F8`
- Aurora Lavender `#A99DFB`
- Horizon Blue `#5DA7F7`
- Aurora Mint `#68DDD2`
- Dawn Coral `#F28B82`
- Cloud Lavender `#F4F2FA`
- Mist `#777482`

Signature gradient is an **event**, not a wallpaper. Reserve it for meaningful improvement/achievement/Aura moments.

Recommended primary font: Plus Jakarta Sans with system fallback. Ensure the actual font-loading strategy does not block rendering or violate privacy/content-security policy.

## Migration order

1. create centralized semantic tokens;
2. map legacy colors/radii/typography to tokens;
3. replace product naming;
4. migrate major layout hierarchy;
5. add destination/target/deadline context;
6. add Aura only at functional moments;
7. run contrast, keyboard, reduced-motion and responsive QA.

Do not scatter raw hex values across components after token migration.

## Onboarding flow

Preferred progressive sequence:

```text
Welcome to ARUORA
→ What are you working toward?
→ Scholarship / Study / Work / Retake / Other
→ Destination (optional/contextual)
→ Target IELTS
→ Deadline / exam month
→ Placement
→ Result
→ Journey
→ Today's Training
```

Do not require every optional field before the learner can experience value.

## Placement result hierarchy

1. estimated overall / current estimate;
2. directly assessed per-skill results;
3. coverage/confidence;
4. gap to target;
5. biggest gap;
6. recommended next action;
7. clear estimated-score disclaimer.

Avoid a false-precision readiness percentage unless WS20's readiness contract is implemented.

## Aura placement

Good surfaces:
- onboarding completion;
- placement result;
- recommendation explanation;
- meaningful improvement;
- empty state;
- optional matching/human-help later;
- reminder/re-engagement.

Avoid:
- permanent floating obstruction;
- repeating the mascot on every card;
- using Aura as the icon for security errors, destructive actions, or functional controls;
- long chat bubbles during timed practice.

## Aura voice implementation

Store approved reusable copy separately from generated freeform responses where practical.

Generated Aura response must follow:
- no official-examiner claim;
- no guilt/shame;
- no guaranteed outcome;
- no fabricated user history;
- acknowledge low confidence;
- do not expose hidden system prompts/rubrics.

Example style:

> “Writing is still the largest gap. Your last two attempts were less consistent than Reading. A focused Task 2 session is the best next step.”

The exact evidence must actually exist before Aura says it.

## Accessibility

Brand fidelity never overrides accessibility.

Required:
- WCAG 2.2 AA target for core flows;
- visible focus;
- keyboard operation;
- screen-reader names;
- touch targets around 44px where practical;
- color-independent correct/error states;
- reduced-motion support;
- sound optional/mutable;
- no essential information conveyed only by mascot expression.

## Brand QA gate

Before merging a major UI rebrand, run the checklist from `../brand-source/10_BRAND_GOVERNANCE_CHECKLIST.md` plus the production accessibility checks in `13_FRONTEND_ROUTING_ACCESSIBILITY.md`.

## Acceptance criteria

- ARUORA tokens are centralized;
- existing learning behavior is preserved unless intentionally changed;
- Destination/Target/Next Action hierarchy is visible;
- Readiness/score language remains truthful;
- Aura is contextual rather than decorative noise;
- mobile layout is not a compressed desktop dashboard;
- dark mode is restrained rather than neon/cyberpunk;
- accessibility regressions block merge.

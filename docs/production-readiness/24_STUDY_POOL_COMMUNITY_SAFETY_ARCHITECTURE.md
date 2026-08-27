# 24 — Study Pool, Future Study Pods, and Community Safety Architecture

## Goal

Prepare the data/security model for validated peer learning without prematurely building a social network.

## Stage 1 — Study Pool only

Initial public beta may collect explicit opt-in fields:
- open to peer practice;
- target band;
- current estimate range;
- preferred skill;
- exam/deadline window;
- coarse availability;
- optional timezone;
- preferred communication inside ARUORA.

Default: **not opted in**.

Do not expose:
- email;
- phone/WhatsApp number;
- exact home address/location;
- private essay/audio history;
- legal name unless separately chosen for profile display.

## Stage 2 — Manual Study Pods

Only after enough opt-in demand exists, operations may manually group 4–8 compatible learners.

Initial matching should be explainable heuristics, not ML:
- target band proximity;
- current level proximity;
- shared skill focus;
- similar exam/deadline window;
- overlapping availability;
- language/timezone constraints where needed.

Record a matching reason for audit and learning.

## Stage 3 — Community Beta

Build pod management/scheduling/reputation only if manual Pods show actual participation and repeat value.

Do not build:
- follower counts;
- global popularity ranking;
- open DMs by default;
- public feed;
- public leaderboard.

## Peer feedback trust model

Peer feedback must be visibly labeled as peer feedback. It must not overwrite calibrated ARUORA score records.

Use structured prompts/rubrics where legally permitted and product-validated.

Future reputation signals may include:
- completed peer sessions;
- feedback helpfulness;
- reliability/attendance;
- verified result/outcome where consented and verified;
- moderation history.

A high IELTS score alone never grants tutor authority.

## Safety controls required before live peer interaction

- explicit community terms/code of conduct;
- report;
- block;
- leave Pod;
- moderation/admin queue;
- abuse/spam limits;
- audit trail;
- privacy-safe profile controls;
- age/minor policy consistent with WS12;
- no forced external contact disclosure.

For synchronous features, define who can invite whom and how join links expire.

## Data model preparation

Do not create every future table now. Document likely boundaries so current migrations do not block them:

```text
peer_preferences
study_pool_membership
study_pod
study_pod_member
peer_session
peer_feedback
moderation_report
block_relation
```

Each future user-owned/relationship row must have clear authorization and deletion behavior.

## Kill criteria

Stop investing in community automation if manual trials show:
- low opt-in;
- low invite acceptance;
- low completed sessions;
- high safety/moderation burden;
- no retention/learning benefit;
- users overwhelmingly prefer solo/human expert help.

## Acceptance criteria for initial public beta

Only Study Pool opt-in is permitted before community validation, and it must:
- default off;
- be revocable;
- be exportable/deletable;
- reveal no direct contact information;
- have analytics events for opt-in/out;
- not create public profiles automatically.

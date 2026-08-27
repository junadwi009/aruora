# 19 — Implementation Tracker

Use this file in the integration branch. Keep issue/PR links beside each item.

| Workstream | Status | Branch/PR | Owner | Blocking issue | Last verified |
|---|---|---|---|---|---|
| WS02 Scoring integrity | NOT STARTED | | | | |
| WS04 Multi-user isolation | NOT STARTED | | | | |
| WS05 LLM security | NOT STARTED | | | | |
| WS13 Frontend routing/a11y | NOT STARTED | | | | |
| WS03 Identity/session | BLOCKED by WS04 | | | | |
| WS08 DB/backup/DR | BLOCKED by WS04 direction | | | | |
| WS07 Jobs/rate/cost | IN PROGRESS (core implemented on `master` working tree 2026-08-27) | — | | WS08/WS15 own staging rollout of Redis+worker topology; WS27 extends (do not duplicate) the `ai_usage_ledger` | 2026-08-27 |
| WS09 API/edge | BLOCKED by WS03 contract | | | | |
| WS10 Observability | BLOCKED by WS07/WS09 shape | | | | |
| WS06 Speaking/audio | BLOCKED by WS05/WS07 | | | | |
| WS12 Privacy/compliance | READY for policy work | | | | |
| WS11 CI/CD | PARTIAL; can prepare then integrate | | | | |
| WS14 Validation | BLOCKED by core integration | | | | |
| WS15 Deployment | BLOCKED by staging topology | | | | |
| WS16 Release gates | BLOCKED until candidate | | | | |
| WS27 AI token economy/task pooling | BLOCKED by WS04/WS05 direction; design READY | | | | |

## Status vocabulary
- `NOT STARTED`
- `READY`
- `IN PROGRESS`
- `PARTIAL`
- `BLOCKED`
- `REVIEW`
- `DONE`
- `ACCEPTED RISK`

## Integration rule
A workstream becomes `DONE` only after its branch is integrated and its acceptance tests pass on the integration branch. “Agent finished coding” is not `DONE`.

## ARUORA v2 workstreams

| WS | Scope | Status | Branch/PR | Evidence |
|---|---|---|---|---|
| WS20 | Product/domain contract | NOT_STARTED | | |
| WS21 | Analytics/cohorts/WML | NOT_STARTED | | |
| WS22 | UAT/Founding Beta operations | NOT_STARTED | | |
| WS23 | Brand/UI/Aura implementation | NOT_STARTED | | |
| WS24 | Study Pool/community-safe preparation | DEFERRED_UNTIL_SIGNAL | | |
| WS25 | WhatsApp/re-engagement | DEFERRED_UNTIL_SIGNAL | | |
| WS26 | Human escalation/monetization boundary | DESIGN_ONLY | | |
| WS27 | AI usage ledger + shared task bank/replenishment | READY_FOR_DESIGN | | |
| WS28 | Auto-RAG Knowledge Pipeline | READY_FOR_DESIGN | | Depends on WS05/WS08 direction; coordinate WS07/WS27 |

## Cohort evidence log

| Cohort | Build SHA | Users | P0/P1 | Key funnel | Decision | Notes |
|---|---|---:|---|---|---|---|
| internal_qa_01 | | | | | | |
| lecturer_uat_01 | | | | | | |
| linkedin_uat_01 | | | | | | |
| founding_beta_01 | | | | | | |

# 13 — Frontend Routing, Failure UX, and Accessibility

## Goal
Make the React client behave like a public application: routable, resilient to backend failure, accessible, and explicit about score uncertainty.

## Current baseline
The reviewed frontend is modular by feature but navigation is largely state/context driven. This works for a prototype but weakens refresh, browser history, deep links, analytics, and protected-route semantics.

## WS13 ownership
Expected areas:
- `web/src/App.tsx`
- `web/src/lib/journey.tsx`
- menu/view context
- auth/protected-route components
- route-level lazy loading/error boundaries
- accessibility tests/config

Avoid backend auth or database edits.

## Task WS13-01 — Route-based navigation
Introduce one routing solution (React Router is a natural conservative choice; another mature router is acceptable).

Suggested route contract:
```text
/
/login
/register
/forgot-password
/reset-password
/onboarding
/placement
/placement/results
/app
/app/reading
/app/listening
/app/writing
/app/speaking
/app/pronunciation
/app/vocabulary
/app/mock-test
/app/progress
/app/settings
```

Use nested routes for the authenticated shell. Do not expose sensitive result content in URL query strings.

## Task WS13-02 — Route guards
Route state must distinguish:
- auth check loading;
- authenticated;
- unauthenticated;
- backend/auth service unavailable;
- onboarding incomplete;
- account requires email verification;
- admin-only.

Do not treat auth-status network failure as “unlocked”. Show a retriable service error/offline state instead. Backend remains authoritative, but frontend should fail visibly rather than optimistically.

## Task WS13-03 — Preserve state safely
- Browser back/forward should work.
- Refresh on a deep authenticated route should return to that route after auth resolution.
- Unsaved essay/speaking work should have a deliberate local draft policy.
- Never put access/session/reset tokens in `localStorage`.
- Reset tokens should be removed from visible URL/history as soon as safely consumed or exchanged.

## Task WS13-04 — API failure UX
Create consistent states for:
- validation error;
- unauthorized/session expired;
- rate limit/quota;
- AI provider unavailable;
- job queued/running;
- job failed/retryable;
- network offline;
- maintenance/service unavailable.

Do not surface provider stack traces or generic “Something went wrong” where a safe actionable status exists.

## Task WS13-05 — Async job UX
For LLM/ASR jobs:
- submit once with idempotency key;
- navigate/display a job state;
- poll with bounded backoff or use SSE where justified;
- allow cancel only when backend supports it;
- resume job status after refresh;
- distinguish queued from failed.

Do not re-submit a paid task on page refresh.

## Task WS13-06 — Truthful score UI
Every AI score display should show:
- “estimated/practice” status;
- scoring method/version in detail/help view where useful;
- missing evidence (e.g. pronunciation not assessed from transcript-only path);
- CEFR as approximate alignment, not exact equivalence;
- link/reference to official IELTS information rather than impersonating an official result form.

Avoid visual treatment resembling an official IELTS Test Report Form.

## Task WS13-07 — WCAG 2.2 AA target
W3C recommends current WCAG and many organizations target Level AA. Treat WCAG 2.2 AA as the product accessibility target.

Priorities for this app:
- full keyboard navigation;
- visible focus not obscured;
- semantic headings/landmarks;
- form label/error relationships;
- accessible authentication (allow password managers/paste);
- minimum target sizes;
- no color-only score/status meaning;
- contrast;
- dialogs trap/restore focus correctly;
- screen-reader labels for timers/progress;
- captions/text equivalents for instructional audio where applicable;
- speaking recorder usable without pointer-only controls;
- reduced-motion support where motion exists.

## Task WS13-08 — Automated + manual accessibility tests
CI:
- axe or equivalent on critical pages;
- component tests for dialog/focus/labels;
- Playwright keyboard smoke.

Manual release checks:
- keyboard-only critical journey;
- one screen reader smoke on desktop;
- mobile zoom/reflow;
- contrast review;
- no inaccessible auth puzzle requirement.

Automated tools cannot certify WCAG conformance alone.

## Task WS13-09 — Performance
- lazy load large feature screens/libraries;
- set immutable caching for hashed assets;
- keep first authenticated shell bundle bounded;
- avoid bundling server-only secrets/config;
- measure Core Web Vitals if public traffic warrants it.

Do not optimize by removing accessibility semantics.

## ARUORA UI migration requirements

Follow `23_BRAND_UI_AURA_IMPLEMENTATION.md` and the source design tokens.

Critical home hierarchy:

```text
Destination
Target
Current estimate / evidence
Today's recommendation
Biggest gap
Progress
Deadline
Flow
```

Readiness must outrank Flow/streak. Aura appears when she adds context, not as a permanent floating decoration.

The route migration should make key states deep-linkable/recoverable without exposing private result identifiers that another user can guess and open.

Add reduced-motion support for Aura/achievement animations and ensure color is not the only carrier of correct/error/progress states.

## Exit criteria
All major screens have stable URLs, auth outages fail visibly, paid jobs survive refresh without duplicate submission, score UX is non-misleading, and critical journeys meet automated/manual accessibility checks toward WCAG 2.2 AA.

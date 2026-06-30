# registration-journey — 2026-06-29

Phase 3c: wire the accounts (3a) into the journey so Login/Register are finally visible and registration happens **after** placement.

## What changed
- **`lib/journey.tsx`**: added `login` + `register` steps.
- **Welcome**: "I already have an account" → `login` (was a dev shortcut to `app`).
- **`auth/AuthScreens.tsx`**: `LoginScreen` (→ `app` on success) + `RegisterScreen` (→ `program` on success; "Maybe later" → `program` anonymously). `AuthForm` gained optional `onSkip`.
- **Results**: CTA "Save your results" → `register` (was straight to `program`). After placement the learner registers to keep their results; the anonymous session profile already owns the placement data, so register just attaches email/password to it.
- **App.tsx**: `login`/`register` cases in the journey switch.

## Flow
Welcome → **Get started** → onboarding (anonymous, sets session) → placement → generating → results → **Register** (or "Maybe later") → program → milestones → app. Returning: Welcome → **I already have an account** → Login → app.

## Verify
- web `npm test` → 46 (results CTA test updated); tsc clean; build OK.
- e2e reworked for the new entry flow (the old "already have a profile → app" shortcut is gone). **4/4 green** against the live stack: load smoke, Welcome→sign-in, Welcome→Get started→onboarding, and a real **API-seeded account signing in through the UI**.

## Caveats
- A signed-in account with no completed placement lands on Welcome (App enters the shell only when `skillLevels` is non-empty). Returning users who finished placement go straight to the app.
- e2e no longer drives the in-app screens (they sit behind a real account + placement); those features stay covered by vitest.

## Commit
- `87a6880` feat(web): registration-after-placement journey + login

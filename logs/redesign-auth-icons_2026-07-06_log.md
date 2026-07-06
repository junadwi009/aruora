# Redesign follow-up — auth screen ink marks — 2026-07-06

Small consistency pass finishing the "Study Desk" identity: the auth screens were the
last place still using the old `linear-gradient(135deg,…)` brand icon (the fingerprint
retired everywhere else).

## What changed (files — presentation only)
- `auth/AuthForm.tsx` (Login + Register), `auth/ForgotPassword.tsx`,
  `auth/PasscodeGate.tsx`, `auth/ResetPassword.tsx` — the icon badge gradient →
  solid **ink mark** (`bg-[var(--color-text)]` + `shadow-e2`, glyph
  `text-[var(--color-surface)]`), matching the Sidebar / Welcome mark.

## Why
Consistency — after Batch 6 these were the only screens left with the gradient mark.

## How to test / verify
- `cd web && npx tsc --noEmit && npm test` → clean, 66 passed (`authform.test.tsx`,
  `passcode.test.tsx` unaffected — select by role/text).
- Verified live in the owner's Chrome (after `docker compose up --build web`): the Login
  screen shows the solid ink mark instead of the indigo gradient circle.

## Caveats
- Presentation-only; no logic/i18n/route change.

## Commit
- `0313d90` — feat(ui): unify auth screen brand marks to the ink mark.

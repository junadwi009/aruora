# Update log — Google sign-in routing + set-password + dashboard layout fix

**Date:** 2026-07-17
**Commit:** _(fill after commit)_

## What changed & why

### 1. Google sign-in routing (new vs returning)
A first-time Google sign-in should go through placement (not land on an empty
dashboard); a returning Google user should go straight to the dashboard.

- **Backend** (`api/app/data/repositories.py`) — `upsert_google_user` now returns
  `(user, is_new)`; `is_new` is True only when a brand-new account is created for
  that `google_sub` (not when linking to an existing same-email account).
- **Backend** (`api/app/routes/account.py`) — `/api/account/google` returns
  `isNew` alongside the user; `_public()` now includes `hasPassword`.
- **Frontend** — `isNew` threads through `api.accountGoogle` → `GoogleButton`
  (new `onGoogleAuthed(user, isNew)` prop) → `AuthForm` → `LoginScreen`, which
  routes `isNew ? "onboarding" : "app"`. Email/password login is unchanged
  (→ dashboard). The post-placement **Register** screen keeps its old Google
  behaviour (→ program) — the isNew routing is scoped to the Welcome→Login path.

### 2. Add a password for Google-only accounts (Settings → Security)
Users who signed in with Google had no way to also use email/password.

- **Backend** (`api/app/routes/account.py`) — `/api/account/password`: if the
  signed-in account has no local password yet, set one directly (no current
  password required); otherwise the existing verify-current-then-change path.
  New repo helper `has_password(user_id)`.
- **Frontend** — `SecuritySection` gains a "set password" mode (no current-password
  field, explanatory hint) shown when `account.hasPassword === false`; `Settings`
  passes `hasPassword`. Aligned the min-length check to the backend's 8 chars
  (was 6 — would have caused a confusing server rejection).

### 3. Dashboard layout fix (from prior turn, folded in)
`menu/Home.tsx` — on a fresh account with no streak/exam data, the right-hand rail
was absent, leaving the right third empty. The main column now spans full width
(`lg:col-span-12`) until there's rail data, then switches to the 8/4 split.

## New i18n keys (EN + ID)
`set.setPassword`, `set.setPasswordHint`, `set.passwordSetDone`; updated
`set.passwordMinChars` to say 8.

## How to test
- Backend: `cd api && .venv/Scripts/python -m pytest tests/test_google_auth.py -q`
  (4 new tests: isNew new→returning, link-existing-not-new, set-first-password,
  password-account-still-needs-current). Full suite: 181 passed.
- Web: `cd web && npx tsc --noEmit && npm run build && npm test` (66 passed).
- Live (manual — real OAuth can't be automated): click **Continue with Google** on
  the Login screen. First-time account → onboarding/placement; returning → dashboard.
  Then Settings → Security shows "Set password" for the Google account.

## Caveats
- Live Google OAuth flow was not automated (real Google auth + credential handling);
  logic is covered by backend unit tests + typecheck.
- Registering via Google on the *post-placement* Register screen still creates a
  separate account rather than attaching to the anonymous placement profile
  (pre-existing behaviour, out of scope here).

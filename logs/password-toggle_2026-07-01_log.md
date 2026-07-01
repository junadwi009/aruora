# password-toggle — 2026-07-01

Owner: add a "see password" button.

## What changed (`341dd40`)
- New reusable `web/src/components/ui/PasswordInput.tsx` — an `<input>` with a
  show/hide **eye toggle**: switches `type` between `password`/`text`, button is
  `tabIndex={-1}` (doesn't break tab flow), `aria-label` flips
  `auth.showPassword` ↔ `auth.hidePassword`, `aria-pressed` reflects state.
- Applied it (drop-in, same className/props) to every password field:
  - `AuthForm` (sign-in / register)
  - `SecuritySection` (current + new password)
  - `ResetPassword` (new password)
- i18n `auth.showPassword` / `auth.hidePassword` (EN + ID).

## Verify
- `tsc` clean; `vitest run` → 55 passed; dictionary parity 484 = 484.
- Live (docker compose up --build web): on the sign-in screen, typing a password
  then clicking the eye reveals the text (`type` password→text) and the icon/aria
  flips to "Sembunyikan kata sandi". Confirmed in Chrome.

## Commit
- `341dd40` feat(auth): show/hide password toggle (eye button)

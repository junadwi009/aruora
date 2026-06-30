# password-reset — 2026-06-29

Phase 4-auth: **forgot/reset password** (the missing piece — 3e only had logged-in change-password). SMTP-optional so it works now and sends real email once SMTP is configured.

## What changed
- **`services/mailer.py`** (new): `send_email(cfg, to, subject, body)` — sends via stdlib `smtplib` when `SMTP_HOST` is set, else logs the message at WARNING (so the dev reset link is visible) and returns False. Never crashes the request on mail failure.
- **`config.py`**: `SMTP_HOST/PORT/USER/PASSWORD/FROM` + `APP_BASE_URL` (for the reset link).
- **`routes/account.py`**: `POST /api/account/forgot {email}` → if the account exists, emails an `itsdangerous`-signed reset link (`?reset_token=…`, 1-hour TTL); **always 200** (no account enumeration). `POST /api/account/reset {token,newPassword}` → validates the token (400 invalid/expired, 422 short) and sets the password. Both added to the timeout-gate open paths.
- **web**: client `accountForgot`/`accountReset`. `AuthForm` gains a "Forgot your password?" link (login mode) → `ForgotPassword` screen (`forgot` journey step). The emailed link opens the app with `?reset_token=…`; `App` detects it and shows `ResetPassword` (takes precedence over the journey).

## Verify
- api `pytest -q` → 116 passed (+3: unknown-email still 200, forgot→reset round-trip, bad-token 400). web `npm test` → 47; tsc clean; build OK.
- Live (no SMTP): register → `forgot` → reset link logged → `reset` (token from log) → 200; old password → 401, new password → 200. Unknown email → still 200.

## Caveats
- No real email until `SMTP_*` is set; in dev the link is in the api log (WARNING). Configure SMTP_HOST/PORT/USER/PASSWORD/FROM + APP_BASE_URL for production delivery.
- Reset tokens are stateless (signed, not stored) — they can't be individually revoked before expiry; 1-hour TTL limits exposure.

## Commits
- `8a65371` feat(auth): forgot/reset password (SMTP-optional email)
- `17c8ce4` fix(mailer): log dev email at WARNING so the reset link is visible

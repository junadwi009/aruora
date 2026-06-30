# Phase 3a Design: Account identity + auth + session timeout

**Status:** approved (verbal) → implementation · **Date:** 2026-06-29 · **Epic:** Phase 3 multi-user accounts

## Goal
Real accounts (email + password) with login/logout and a sliding 30-minute session timeout. Foundation for 3b (data scoping), 3c (registration journey), 3d/3e (Settings). Offline-first preserved: the journey can run anonymously; an account lets you save + return. Google deferred (column reserved).

## Data
`user_profile` gains: `email` (String, unique, nullable), `password_hash` (String, nullable), `google_sub` (String, nullable). Nullable = a profile may exist anonymously (created during onboarding) before credentials are attached. Schema evolves via `create_all` on a fresh DB; the dev volume is recreated for live verification (incremental Alembic migrations remain documented debt). Passwords hashed with Werkzeug (`generate_password_hash`/`check_password_hash`) — no new dependency.

## Backend
- **Repository**: `create_account(email, password, name="", goal="other", target_band=6.0)->user`; `attach_credentials(user_id, email, password)->user`; `get_account_by_email(email)->user|None`; `verify_login(email, password)->user|None`; `set_password(user_id, password)`; `get_user_by_id(id)->user|None`. Email uniqueness enforced (reject duplicate).
- **Session helpers** (`app/session.py`): `login_session(uid)` sets `session["uid"]` + `last_seen`; `current_uid()`; `touch()` refreshes `last_seen`.
- **Routes** (`routes/account.py`): `POST /api/account/register {email,password}` (attaches to the current anonymous session profile if one exists & has no email, else creates a new minimal account; 422 on bad email/short password or duplicate email; logs in); `POST /api/account/login {email,password}` (verify → session; 401 on bad creds); `POST /api/account/logout`; `GET /api/account/me` (→ profile or 401).
- **Timeout gate** (`before_request`): if a session has `last_seen` and now − last_seen > 30 min → `session.clear()`; for protected `/api/*` (all except health + account/login/register/logout) return 401 `SESSION_EXPIRED`; otherwise refresh `last_seen`. Coexists with the optional `APP_PASSCODE` gate. `SESSION_TIMEOUT_MIN` configurable (default 30).
- **Errors**: add `UNAUTHORIZED`(401) / `SESSION_EXPIRED`(401) / `CONFLICT`(409) usage.

## Frontend
- `client.ts`: `accountRegister`, `accountLogin`, `accountLogout`, `accountMe`. On any 401 `SESSION_EXPIRED`, the client emits a logout event → app returns to Welcome/Login.
- Components `auth/Login.tsx` + `auth/Register.tsx` (email + password fields, validation, error). Login reachable from Welcome's "I already have a profile" (repurposed → Login). Full registration-after-placement wiring is **3c**; here Register works standalone + Login works.

## Testing (TDD)
- api: register→login→me→logout happy path; duplicate email → 422; wrong password → 401; idle > timeout (stale `last_seen`) → 401 SESSION_EXPIRED + session cleared; password is hashed (not stored plaintext).
- web: client method URLs; Login/Register smoke (submit calls client; error on failure).

## Boundary
3a is pure auth/identity. It does **not** scope existing data (that's 3b) or reorder the journey (3c). Anonymous sessions keep working; the timeout only affects established sessions.

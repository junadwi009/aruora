# accounts-auth — 2026-06-29

Phase 3a: real accounts (email + password) with login/logout and a sliding 30-minute session timeout. Foundation of the Phase 3 multi-user epic. Google deferred (column reserved).

## What changed
- **`user_profile`** += nullable `email` (unique), `password_hash`, `google_sub` (OAuth-reserved). Nullable so a profile can exist anonymously before credentials attach.
- **Repo**: `create_account` / `attach_credentials` / `get_account_by_email` / `verify_login` / `set_password` / `get_user_by_id` (Werkzeug `generate_password_hash`/`check_password_hash` — no new dep).
- **`app/session.py`**: `login_session` / `current_uid` / `touch` / `clear_session` with a `_now()` indirection (so tests fast-forward the clock).
- **`routes/account.py`**: `POST /api/account/register` (attaches to the current anonymous session profile if it has no email, else creates one; 422 on bad/duplicate email or short password; logs in), `/login`, `/logout`, `GET /api/account/me`.
- **`__init__.py`**: a `before_request` **sliding-timeout** gate — when a session's `last_seen` is older than `SESSION_TIMEOUT_MIN` (default 30) it clears the session and returns `SESSION_EXPIRED` 401 for protected routes; otherwise refreshes `last_seen`. Fixed a name shadow (top-level `from flask import session` was hiding the `app.session` submodule → the timeout monkeypatch failed); now imports the submodule explicitly and uses flask's session locally.
- **web**: client `accountRegister/Login/Logout/Me` + `AccountUser`; on a `SESSION_EXPIRED` response the client fires `window` event `ielts:session-expired` and `App` reloads to the sign-in screen. Shared `AuthForm` (login/register modes). **Not yet wired into the journey — that's 3c.**

## Bug fixed (exposed by fresh-DB verification)
- **Seeding race:** with a fresh volume, both gunicorn workers ran `seed_all` past the "combos empty" check and both inserted the Day-1 lesson → `duplicate key … lessons_pkey`, api failed to boot. `seed_all` now wraps the insert in `try/except IntegrityError → rollback` (whichever worker loses the race no-ops). Was masked before because the volume always had data.

## Verify
- api `pytest -q` → 103 passed (+5 account). web `npm test` → 46 (+4: AuthForm×3, client); tsc clean; build OK.
- Live (fresh DB volume recreated): register→`{id:1,email}`; me 200; logout→me 401 (cookie saved); login 200; duplicate email 422; wrong password 401. Idle-timeout covered by unit test.

## Caveats
- Schema changes land via `create_all` on a fresh DB — recreating the dev volume wipes prior throwaway data. Incremental Alembic migrations remain documented debt (will matter for 3b's column adds on a populated prod DB).
- Single shared passcode gate (2e-1) still coexists, off by default.

## Commits
- `2e2280f` feat(api): account identity + auth + timeout · `b281f99` feat(web): account client + AuthForm · seed-race fix (this commit)

# tips-collapse-remember-me — 2026-07-01

Three owner requests: (1) make the Tips criteria card collapsible, (2) turn the
skill toggle into a dropdown, (3) add "Remember me" that forgets after 7 days idle.

## What changed

### Tips criteria card — collapsible + dropdown (`a33b557`)
- `TipsSidePanel.tsx`: the "Kriteria Penilaian Mandiri" card header is now a
  toggle button with a rotating chevron (`criteriaOpen` state); the ladder + hint
  live in a collapsible panel (`aria-expanded`/`aria-controls`).
- The 2×2 skill toggle is replaced by a `<select>` dropdown (Reading / Listening /
  Writing / Speaking), `aria-label`ed. Selecting a skill still swaps the ladder.

### Remember me — 7-day sliding forget
Backend (`c243b99`):
- `config.REMEMBER_DAYS` (default 7).
- `session.login_session(uid, remember)` stores a `remember` flag and sets
  `session.permanent = remember` (so a remembered cookie survives a browser
  restart; a non-remembered one is a session cookie).
- `create_app` sets `app.permanent_session_lifetime = timedelta(days=REMEMBER_DAYS)`.
- The `before_request` idle-timeout gate uses a `REMEMBER_DAYS`-day sliding window
  when the session is remembered, else the 30-min default → the session is
  forgotten after 7 days of inactivity.
- `/api/account/login` reads `remember` from the body.

Frontend (`1d3aaa7`):
- `AuthForm`: a "Remember me" checkbox (default on, login mode only) with the hint
  "(forgets after 7 days idle)"; sends `remember` to `accountLogin`.
- `api.accountLogin` accepts `remember`; i18n `auth.remember` / `auth.rememberHint`
  (EN + ID).

## Verify
- api: `pytest -q` → **143 passed** (new `test_remember_me_extends_timeout_to_seven_days`:
  no-remember expires at 31 min; remember survives 31 min and expires at 8 days).
- web: `tsc` clean; `vitest run` → **55 passed**.
- Live (docker compose up --build):
  - `POST /account/login` with `remember:true` → `Set-Cookie … Expires=Wed, 08 Jul
    2026 …` (7-day persistent); without → session cookie (no Expires).
  - In Chrome: login shows "☑ Ingat saya (lupa setelah 7 hari tak dipakai)";
    Tips criteria card collapses/expands from its header; skill dropdown swaps the
    ladder.

## Notes
- "Forget after 7 days" is a sliding idle window: each request refreshes both the
  server-side `last_seen` and the cookie lifetime, so 7 days of *inactivity* logs
  the user out. Active users stay signed in indefinitely.
- Register still logs in without remember; the checkbox is on the sign-in form.

## Commits
- `c243b99` feat(auth): remember me with 7-day sliding forget (backend)
- `1d3aaa7` feat(auth): Remember me checkbox on sign-in (EN+ID)
- `a33b557` feat(tips): collapsible criteria card + skill dropdown

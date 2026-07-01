# google-signin — 2026-07-01

Wired "Sign in with Google" using the owner's OAuth Web-client ID (added to the
gitignored `.env` as `GOOGLE_CLIENT_ID`). Approach ①: Google Identity Services
token → backend verifies → find/create user by the existing `google_sub` column.

## What changed

### Backend (`807b716`)
- `config.GOOGLE_CLIENT_ID` (public web-client id; empty = Google disabled).
- `requirements.txt`: `google-auth==2.35.0` (imported lazily so tests need it not).
- `POST /api/account/google {credential}` — `verify_google_id_token()` checks the
  ID token against `GOOGLE_CLIENT_ID` (returns claims or None; isolated so tests
  monkeypatch it). Then `repo.upsert_google_user(sub, email, name)`:
  find by `google_sub` → else link to an existing same-email account → else create
  a password-less account. Then `login_session`. 501 if not configured, 401 on a
  bad token.
- `/api/health` now returns `googleClientId` (public) so the SPA can render the
  button without a build-time env var.
- Added `/api/account/google` to the idle-timeout open-paths.

### Frontend (`afef719`)
- `GoogleButton` component loads the GIS script and renders the official button;
  the returned credential is POSTed via `api.accountGoogle`.
- `AuthForm` fetches `googleClientId` from `/health` and, when present, shows an
  "or" divider + the Google button (login & register). `AccountUser`/client typed;
  `auth.or` key (EN+ID). authform.test mocks `api.health`.

## Verify
- api: `pytest -q` → **152 passed** (`test_google_auth.py`: creates account +
  session, idempotent by sub, links same-email account, 401 bad token, 501 when
  unconfigured, health exposes the id).
- web: `tsc` clean; `vitest run` → 55 passed; dictionary parity 482 = 482.
- Live (docker compose up --build): `/api/health` returns the real
  `googleClientId` from `.env`; in Chrome the sign-in screen shows the "atau"
  divider + the GIS **"Continue with Google"** button.
- No client-id/secret value appears in any tracked file (checked); `.env` is
  gitignored.

## Manual step still required (owner, in Google Cloud Console)
- Add the app origin(s) to the OAuth client's **Authorized JavaScript origins**:
  `http://localhost:5173` for dev (and the production URL later). Without it, the
  button renders but sign-in fails with an origin mismatch.
- While the consent screen is in **Testing**, only listed **test users** can sign
  in (add the owner's email). Publish the app for public access.
- Note: `.env` currently has a typo `GOOGLE_CLIENT_SECRETE` — harmless for this
  token flow (the secret isn't used); the Client ID is what matters.

## Commits
- `807b716` feat(auth): Sign in with Google (verify ID token → google_sub)
- `afef719` feat(auth): 'Continue with Google' button on sign-in (GIS)

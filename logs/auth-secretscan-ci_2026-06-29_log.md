# auth-secretscan-ci — 2026-06-29

Phase 2e-1/2/3: the three **critical deploy-readiness** audit fixes — passcode gate, a trustworthy secret scan, and CI.

## 2e-1 Auth passcode gate (`7d81e23`)
- `APP_PASSCODE` (empty = open, the offline-dev default) gates all `/api/*` except `health` + `auth/*` via a signed Flask session cookie. New `routes/auth.py`: `GET /api/auth/status`, `POST /api/auth/login`, `POST /api/auth/logout`. `before_request` enforces the gate; `app.secret_key = SESSION_SECRET`; CORS `supports_credentials=True`; client sends `credentials:"include"`.
- Frontend `App.tsx` checks `authStatus` on load and renders `PasscodeGate` when `authRequired && !authenticated` (fails **open** if the status route is unreachable, so a broken api never locks you out permanently).
- `.env.example` documents `APP_PASSCODE` + `SESSION_SECRET`.
- Verified live: open stack → `authRequired:false`; a one-off container with `APP_PASSCODE=secret123` → `authRequired:true`, protected route `401`, wrong passcode `401`. Unit: api 98 (+2), web 37 (+2).

## 2e-2 Secret scan fix (`4185e28`)
- The old scan flagged legit server-side `cfg.OPENROUTER_API_KEY` references in `api/app` and printed FAILED while exiting 0. Rewritten to scan **only `web/dist`** (the browser-visible artefact) for actual key VALUE patterns (`sk-or-v1-…`, `sk-ant-…`, long `sk-…`) with a real non-zero exit. Verified: clean tree → exit 0; planted key → exit 1.

## 2e-3 CI (`3a70cb5`)
- `.github/workflows/ci.yml`: **api** job (install requirements + spaCy model → pytest) and **web** job (npm ci → tsc → vitest → build → secret_scan.sh). Mirrors the locally-green checks. Playwright e2e stays local (needs the compose stack + browsers). YAML validated.

## Caveats
- Auth is a single shared passcode (not per-user); session cookie is signed, not encrypted. Good enough for a private single-user instance; not multi-tenant.
- CI installs the full api requirements (faster-whisper/spaCy) so the first run is a few minutes; the model download is cached by `setup-python`'s pip cache only partially.
- CI not yet observed green on GitHub (no push performed) — commands are the same ones passing locally.

# Docs v3 context fix — 2026-07-05

Corrected stale documentation that still described the legacy v1 stack, so future
sessions orient from accurate context (Phase 0 of the audit/redesign engagement).

## What changed (files)
- `CLAUDE.md` — **rewritten** from the v1 description (Express + vanilla ESM +
  `node:sqlite` + Anthropic SDK) to a concise (<60 line) v3 map: Flask/WSGI +
  React 19/Vite/Tailwind v4 + Postgres + OpenRouter. Preserves the hard rules
  (update-log, SDD, i18n, multi-user scoping, stay-in-stack) and the owner profile.
  Note: `CLAUDE.md` is git-ignored (root `.gitignore`) → local context only, not committed.
- `README.md` — 4 surgical edits:
  - Architecture table: "Python FastAPI backend" → "Python Flask backend, WSGI via `gunicorn wsgi:app`".
  - Dev run: `uvicorn app.main:app --reload` → `gunicorn -b 0.0.0.0:5050 wsgi:app` (+ flask dev alt). (`app.main` module never existed; entry is `api/wsgi.py`.)
  - "Python 3.11+" → "Python 3.13" (matches `api/Dockerfile`).
  - "Before exposing publicly" block: replaced the outdated "the app has no auth"
    bullet — the app now has email/password + Google Sign-In + optional passcode +
    rate limiting; added the `SESSION_SECRET` required / `COOKIE_SECURE` note.

## Why
Documented drift (D1–D5) found in Phase 0: `CLAUDE.md` was v1; `README.md` claimed
FastAPI/uvicorn, wrong Python version, and "no auth" (all contradicted by the code).

## How to test / verify
- `grep -n "FastAPI\|uvicorn\|no auth" README.md` → no matches.
- `head -1 CLAUDE.md` → "# CLAUDE.md — IELTS Coach v3".
- README run commands match `api/Dockerfile` (`gunicorn ... wsgi:app`) and `api/wsgi.py` exists.

## Caveats
- Docs-only change; no code, no behavior change. Tests unaffected.
- `CLAUDE.md` stays git-ignored by design (root global ignore). If you want the v3
  version tracked, it must be explicitly un-ignored/force-added — not done here.

## Commit
- `a1a396c` — README.md + this log. `CLAUDE.md` is git-ignored (refreshed locally only). Not pushed.

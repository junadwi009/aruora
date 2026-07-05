# Security audit + hardening — 2026-07-05

Full end-to-end security review of the v3 stack (Flask API + React/TS web + Postgres + Docker),
followed by remediation of all 12 findings. Analysis was approved before any code change.

## What changed (files)

**Backend — app factory & config**
- `api/app/config.py` — new knobs: `COOKIE_SECURE`, `COOKIE_SAMESITE`, `MAX_CONTENT_BYTES`, `RATE_LIMIT_ENABLED`.
- `api/app/__init__.py` —
  - **Fail-closed guard**: refuses to boot outside tests if `SESSION_SECRET` is the built-in default.
  - Session-cookie flags: `HttpOnly` + `SameSite` (Lax default) + `Secure` (config-driven).
  - `MAX_CONTENT_LENGTH` cap (26 MB) → memory-DoS guard.
  - In-process **rate limiter** `before_request` (disabled under TESTING).
  - **Security headers** `after_request` (nosniff, DENY, no-referrer, restrictive CSP for JSON API).
- `api/app/ratelimit.py` — **new**: dependency-free sliding-window limiter + per-route rule table.
- `api/app/errors.py` — clean JSON handler for `413`.

**Backend — routes**
- `reading.py`, `listening.py`, `vocab.py`, `pronounce.py` — added `_require_uid()` so the **paid-LLM
  endpoints are no longer unauthenticated**.
- `auth.py`, `internal.py` — passcode / reminder-token compared with `hmac.compare_digest` (constant-time).
- `account.py` — password policy raised to **min 8** (shared `_require_password`); **SVG data-URL avatars rejected**.

**Infra / config templates**
- `web/nginx.conf` — CSP + `X-Content-Type-Options` / `X-Frame-Options` / `Referrer-Policy` (HSTS commented, enable under TLS).
- `.env` — added a strong generated `SESSION_SECRET` + `COOKIE_SECURE=0`. **Live third-party keys left untouched (owner deferred rotation — local install).**
- `api/.env.example` — documented `SESSION_SECRET`, `COOKIE_SECURE`, `COOKIE_SAMESITE`, `RATE_LIMIT_ENABLED`, passcode/admin/reminder vars.

**Tests**
- `api/tests/test_security_hardening.py` — **new** (16 tests): secret guard, cookie flags, headers, LLM-auth, password policy, SVG rejection, rate-limiter unit.

## Findings addressed
| # | Sev | Fix |
|---|-----|-----|
| 1 | CRITICAL | `SESSION_SECRET` fail-closed guard + real secret in `.env` + `.env.example` |
| 2 | HIGH | auth guard on reading/listening/vocab/pronounce + rate limiting |
| 3 | HIGH | secrets documented; rotation deferred by owner (local install) |
| 4 | MED | `Secure`/`SameSite`/`HttpOnly` cookie flags |
| 5 | MED | SameSite=Lax + JSON-content-type/CORS as CSRF defence |
| 6 | MED | rate limiting on login/forgot/reset/password |
| 7 | MED | `MAX_CONTENT_LENGTH` + 413 handler |
| 8 | LOW | register enumeration blunted by rate limiting |
| 9 | LOW | constant-time token/passcode compare |
| 10 | LOW | password min 8 |
| 11 | LOW | SVG avatar rejected |
| 12 | LOW | security headers (API + nginx CSP) |

**Verified not vulnerable:** SQL injection (ORM-only), XSS (React auto-escaping, no raw-HTML injection sink, no auth token in localStorage), key leakage (gateway sanitises + CI secret-scan), SSRF (fixed LLM base URL).

## How to test / verify
- `cd api && .venv/Scripts/python -m pytest -q` — full suite green (incl. new `test_security_hardening.py`).
- Boot guard: `python -c "from app import create_app; create_app({'TESTING':False,'SESSION_SECRET':'dev-secret-change-me'})"` → raises `RuntimeError`.
- Headers: `curl -i localhost:5050/api/health` → shows `X-Frame-Options: DENY` etc.
- Auth: `POST /api/vocab` without a session → `401`.

## Caveats / known limits
- Rate limiter is **in-process**: with gunicorn `--workers 2` the effective limit is ~2× per node. Front with Redis for exact global limits / multi-node.
- CSP in `nginx.conf` keeps `style-src 'unsafe-inline'` (app uses inline styles) and allows Google Sign-In origins — tighten if GSI is dropped.
- Register still returns "already registered" (UX). Rate limiting blunts enumeration; a fully non-enumerable flow would change the signup UX.
- Live OpenRouter key + (unused, misspelled) Google client secret remain in `.env` by owner's choice — rotate + move to a secret manager before any public deploy.

## Commit
- Pending (working tree). Not committed — awaiting owner go-ahead.

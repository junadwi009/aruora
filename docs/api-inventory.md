# API Endpoint Inventory (WS09-09)

**Status: the `/api/*` surface is INTERNAL/PRIVATE to the ARUORA web client.**
It is not a versioned public API contract, is subject to change without
notice, and must not be consumed by third parties. Public third-party use
requires formalizing `/api/v1` plus the governance in
`docs/production-readiness/09_API_EDGE_SECURITY.md`.

Cross-cutting controls that apply to EVERY endpoint:

| Control | Value |
|---|---|
| Auth model | Server-side session cookie (`ar_session`, HttpOnly/SameSite/Secure) — no bearer tokens in the browser |
| CSRF | Double-submit: `ar_csrf` cookie echoed in `X-CSRF-Token` on every unsafe method |
| CORS | Absent in same-origin production; exact origin allow-list only if configured (never `*` with credentials) |
| Global body limit | `MAX_CONTENT_BYTES` (26 MB) → 413 `PAYLOAD_TOO_LARGE` |
| Audio limit | `ASR_MAX_UPLOAD_BYTES` (10 MB) on `/api/speaking/transcribe` |
| Error shape | `{"error": {"code", "message", "details", "requestId"}}` — no stacks, no provider payloads |
| Correlation | `X-Request-ID` accepted (sanitized) and echoed on every response |
| Caching | `Cache-Control: no-store` on all `/api/*` responses |
| Host policy | `TRUSTED_HOSTS` allow-list when configured; loopback health probes exempt |
| Rate limits | Redis-backed shared windows in production (in-process fallback for single-worker self-hosts); `429 RATE_LIMITED`, `503 RATE_LIMITER_UNAVAILABLE` (fail closed) |
| Data classification | **Sensitive**: learner content (essays, transcripts, audio), goals/deadlines, scores, account identifiers. **Operational**: job records, usage ledger, analytics events (content-free) |

Rate-limit classes: `credential` = IP + email-hash dimensions (both must allow);
`user` = authenticated user id; `ip` = client IP (never attacker-controllable
forwarded headers — WS09-03); default 300/min per IP.

## Health & internal

| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/api/health` | GET | none | Liveness + public client config (googleClientId, asrReady). No topology (WS09-10) |
| `/api/health/ready` | GET | none | Readiness: db/redis booleans only; 503 drains traffic. No hosts/URLs |
| `/api/admin/health/detail` | GET | admin | Provider mode, ASR probe, queue mode (diagnostics) |
| `/api/internal/reminders/run` | POST | shared `X-Reminder-Token` (constant-time compare) | Cron trigger. Disabled when token unset. Header only — never query string. Idempotent per user/day. Private-network path recommended (WS09-09B) |
| `/api/internal/maintenance/run` | POST | shared `X-Maintenance-Token` | Data-lifecycle sweep (WS08). Same rules as above |

## Identity & account

| Endpoint | Method | Auth | Rate class | Data |
|---|---|---|---|---|
| `/api/auth/status` | GET | none | ip | none |
| `/api/auth/login` | POST | none | credential | passcode (max 256) |
| `/api/auth/logout` | POST | none | ip | none |
| `/api/account/register` | POST | none | credential | email + password (policy-validated) |
| `/api/account/login` | POST | none | credential | email + password + optional TOTP |
| `/api/account/google` | POST | none | credential | Google ID token (server-verified) |
| `/api/account/forgot` / `reset` / `verify` | POST | none / one-time token | credential | email / token + new password |
| `/api/account/logout` | POST | session | ip | none |
| `/api/account/me` | GET | session | ip | account profile (own) |
| `/api/account/profile` | PATCH | session | ip | own profile (server-validated fields) |
| `/api/account/password` | POST | session | credential | current + new password |
| `/api/account/avatar` | POST | session | ip | raster data-URL only (SVG rejected) |
| `/api/account/export` | GET | session | ip | own full export |
| `/api/account` | DELETE | session | ip | hard-deletes own account + children |
| `/api/account/sessions` | GET / DELETE | session | ip | own session list / revoke all |
| `/api/account/sessions/others` | DELETE | session | ip | revoke other devices |
| `/api/account/verify/resend` | POST | session | credential | verification email |

## Admin (env-designated `ADMIN_EMAILS` only; optional TOTP; audited)

| Endpoint | Method | Notes |
|---|---|---|
| `/api/admin/users` | GET | account list |
| `/api/admin/users/<id>` | DELETE | destructive — requires fresh reauthentication |
| `/api/admin/users/<id>/reset-password` | POST | destructive — requires fresh reauthentication |
| `/api/admin/reauth` | POST | password reauth window |
| `/api/admin/stats` / `metrics` / `audit` / `feedback` / `ai-usage` / `ai-budget` | GET/POST | ops + governance surfaces |
| `/api/admin/analytics/summary` | GET | WML + cohort counts (content-free) |

## Learning surface (user-owned; every read/write scoped by `user_id`)

| Endpoint | Method | Auth | Rate class | Notes |
|---|---|---|---|---|
| `/api/onboarding` | POST | none (creates anon profile) | ip | Pydantic contract |
| `/api/placement/start` | POST | session | ip | Pydantic contract |
| `/api/placement/submit` | POST | session | ip | Pydantic contract; LLM scoring |
| `/api/practice/generate` / `status` | POST/GET | session | ip | job submission (idempotency-keyed) |
| `/api/practice/set` | GET | session | ip | pool serve (no LLM) |
| `/api/practice/attempt` | POST | session | ip | Pydantic contract; correct ≤ total |
| `/api/reading/generate` / `listening/generate` | POST | session | user | band validated; pool-first serving |
| `/api/writing/evaluate` | POST | session | user | essay ≤ MAX_ESSAY_CHARS; contract before LLM |
| `/api/speaking/evaluate` | POST | session | user | transcript ≤ MAX_TRANSCRIPT_CHARS |
| `/api/speaking/roleplay` | POST | session | user | history bounded (12 turns, per-turn cap) |
| `/api/speaking/transcribe` | POST | session | user | multipart ≤ ASR_MAX_UPLOAD_BYTES |
| `/api/lesson/today` / `generate` / `<day>` | GET/POST | session | user | focus/band/day contract |
| `/api/vocab` | POST | session | user | topic ≤ 200 chars |
| `/api/pronounce/sentence` / `feedback` | POST | session | user | topic/target/transcript bounds |
| `/api/program` + `/api/program/milestones[...]` | POST/GET/PUT/DELETE | session | ip | Pydantic contract |
| `/api/mocks` | GET/POST | session | ip | IELTS half-band constraint (0–9, 0.5 steps) |
| `/api/history/attempts` / `attempt/<id>` | GET | session | ip | own attempts only (404 cross-user) |
| `/api/stats/trends` / `activity` | GET | session | ip | own aggregates |
| `/api/skill-levels` | GET | session | ip | own CEFR levels |
| `/api/tips/<skill>` | GET | session | ip | static guidance |
| `/api/cards` / `due` / `<id>` / `<id>/review` | CRUD | session | ip | front/back ≤ 1000; quality 0–5 |
| `/api/gate/status` / `heartbeat` / `unlock` | GET/POST | session | ip | UAT feedback gate; seconds clamped |
| `/api/analytics/events` | POST | session/anon | ip | server-side event allow-list; content-free; fabricated events rejected 422 |
| `/api/jobs/<id>` | GET | session | ip | own job status (queued/running/done/failed/expired) |

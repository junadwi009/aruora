# 09 — API and Edge Security

## Goal
Harden the internet-facing boundary and Flask proxy assumptions without breaking the same-origin SPA architecture.

## WS09 ownership
Expected areas:
- `web/nginx.conf` / selected edge config
- Flask app initialization/config
- CORS/proxy/security-header middleware
- request-validation limits
- edge/API security tests

## Task WS09-01 — TLS and public ports
Production:
- serve HTTPS only;
- redirect HTTP to HTTPS if port 80 is exposed;
- publish only the edge/web port;
- API, DB, Redis, workers remain private;
- automate certificate renewal when self-hosted.

Do not enable HSTS preload immediately. Stage HSTS with a short max-age, confirm all required subdomains are HTTPS, then extend.

## Task WS09-02 — Trusted hosts
Flask documentation recommends `TRUSTED_HOSTS` for Host header validation.

Configure explicit production hostnames. Do not generate password-reset/email links from an arbitrary incoming Host header.

Use a configured canonical public origin for security-sensitive external URLs.

## Task WS09-03 — ProxyFix only with exact proxy topology
If Flask is behind one trusted reverse proxy, configure Werkzeug `ProxyFix` only for the forwarded headers that proxy sets and the exact number of trusted proxies.

Do not blindly trust arbitrary `X-Forwarded-*`/`X-Real-IP` from direct clients. Ensure the API port cannot bypass the trusted proxy in production.

## Task WS09-03B — Server-side request contracts everywhere
The reviewed repository already uses Pydantic on some routes, but several public handlers still consume arbitrary JSON via `request.get_json(...); body.get(...)`. Public production input validation must be systematic, not endpoint-specific.

For every public route define a server-side input contract covering:
- allowed/required fields and rejection of unexpected security-sensitive fields;
- string lengths and normalized enums;
- numeric ranges and IELTS half-band constraints where relevant;
- collection cardinality/history limits;
- identifiers and ownership context;
- URL/date/timezone formats;
- multipart MIME/byte/duration rules.

Do not rely on TypeScript/client validation as a security or persistence boundary. Return a stable 4xx validation error and reject before LLM, ASR, database, or other expensive work.

## Task WS09-04 — Same-origin CORS policy
For the production web deployment, prefer no cross-origin browser API access at all. Same-origin `/api` means CORS can be absent/strict.

If a future mobile/external client requires CORS:
- exact allow-list origins;
- never `*` with credentials;
- explicit methods/headers;
- threat-model CSRF/auth separately.

## Task WS09-05 — Security response headers
At the web/edge layer implement and test an appropriate policy:
- `Content-Security-Policy` (begin Report-Only, then enforce);
- `Strict-Transport-Security` after staged rollout;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: strict-origin-when-cross-origin` or stricter if product allows;
- `Permissions-Policy` limiting camera/microphone/etc. to actual needs;
- CSP `frame-ancestors 'none'` (or explicit policy) for clickjacking;
- safe cache policy for authenticated/sensitive responses.

Do not cargo-cult deprecated `X-XSS-Protection` as a primary defense.

## Task WS09-06 — CSP design for this app
Inventory actual script/connect/font/media origins first. Start with `Content-Security-Policy-Report-Only`, collect violations in staging, then enforce.

Prefer self-hosted assets where practical. Google Sign-In or other third-party scripts must be explicitly allowed rather than broad `*` sources.

Do not add `unsafe-inline` broadly just to make CSP pass.

## Task WS09-07 — Request limits
Server/edge limits by route class:
- JSON body max;
- essay/transcript max characters;
- audio max bytes/duration;
- header size;
- multipart parts;
- connection/read timeout;
- upstream timeout appropriate to synchronous endpoints.

As LLM/ASR become queued, reduce long request timeouts rather than holding HTTP workers for minutes.

## Task WS09-08 — Error handling
Public API errors:
- stable code/message shape;
- no stack trace;
- no SQL/provider details;
- no API key/model credentials;
- correlation/request ID for support.

Full exception detail belongs in protected telemetry, with PII/secrets filtered.

## Task WS09-09 — API inventory/versioning
Before public third-party use, formalize `/api/v1` or explicitly state the current API is internal/private to the web app. Maintain an endpoint inventory with:
- auth requirement;
- role;
- ownership rule;
- rate limit;
- body limit;
- data classification.

Do not accidentally create a “public API contract” simply because routes are reachable from the internet.

## Task WS09-09B — Internal scheduler/maintenance endpoints
The reviewed application has reminder/maintenance behavior protected by shared configuration tokens. Public production should minimize externally reachable cron-style control endpoints.

Preferred target:
- execute reminders/cleanup from the worker/scheduler process or a private platform job;
- if an HTTP trigger is unavoidable, keep it on a private/internal network path with workload identity or a rotated secret, strict method, rate limit, and audit event;
- never expose scheduler secrets to the browser or place them in query strings;
- make reminder sends idempotent so scheduler retries cannot duplicate mail.

The global `APP_PASSCODE` may remain as an optional maintenance/private-beta gate, but it is not a replacement for per-user public authentication/authorization.

## Task WS09-10 — Health endpoints
Separate:
- liveness: process can run;
- readiness: can safely serve (DB/required shared services available);
- detailed diagnostics: private/admin/monitoring only.

Do not expose database URLs, provider keys, version secrets, or internal topology in public health responses.

## Product API contracts

New ARUORA profile endpoints must validate controlled fields such as `goal_type`, `target_band`, `cohort_id`, and `acquisition_source` server-side. Client-provided cohort/source should not be trusted when the server can derive campaign/cohort assignment.

Future Study Pool endpoints must use explicit verbs/contracts such as opt-in/update-preferences/opt-out rather than making the user public by creating a profile implicitly.

Future WhatsApp webhooks are machine-to-machine endpoints and must use provider signature verification, replay/idempotency controls, and a security model separate from browser sessions/CSRF.

## Required tests
- untrusted Host rejected;
- direct client cannot spoof rate-limit IP through forwarded header path;
- cross-origin unsafe request rejected by CSRF/origin policy;
- CSP/header snapshot in staging;
- oversized JSON/audio rejected before expensive work;
- production config does not expose API/DB/Redis host ports;
- error responses do not contain stack/secret/provider payload.

## Exit criteria
Only the edge is public, Flask trusts exactly the intended proxy/hosts, same-origin security is explicit, security headers are enforced after report-only validation, and expensive malformed requests are rejected early.

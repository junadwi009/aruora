# Security Design: LLM/ASR endpoint auth hardening (Batch 1)

**Status:** proposed → awaiting approval · **Date:** 2026-07-05 · **Epic:** Post-audit security remediation (Phase 1 audit findings H1, M1, M2)

## Goal
Close the remaining unauthenticated / auth-after-work gaps on the paid-LLM and
compute-heavy ASR endpoints, so no anonymous caller can trigger paid model calls
or expensive local Whisper transcription. Builds on the prior pass (commit
`40e537c`) which secured the `*/generate` endpoints but missed roleplay,
transcribe, and the evaluate/submit ordering.

## Findings addressed
- **H1** — `POST /api/speaking/roleplay` calls the paid LLM with **no** `_require_uid()`. ([speaking.py:47](../../../api/app/routes/speaking.py))
- **M1** — `POST /api/speaking/transcribe` has **no** auth and only the loose global 300/min limit; runs CPU-heavy faster-whisper. ([speaking.py:61](../../../api/app/routes/speaking.py), [asr.py](../../../api/app/services/asr.py))
- **M2** — `writing/evaluate`, `speaking/evaluate`, `placement/submit` invoke the LLM (and spaCy metrics) **before** the `_require_uid()` gate, so unauth requests still do the paid/heavy work before returning 401. ([writing.py:36](../../../api/app/routes/writing.py), [speaking.py:18](../../../api/app/routes/speaking.py), [placement.py:38](../../../api/app/routes/placement.py))

## Design
No schema change. No new dependency. No API-contract change for authenticated
callers (same request/response shapes and status codes on the happy path).

- **Auth-first ordering.** Each affected handler calls `_require_uid()` as its
  **first** statement, before any `_gateway()` / `compute_metrics()` / ASR work.
  For H1 (roleplay) and M1 (transcribe) this adds the guard that was absent; for
  M2 it moves the existing guard to the top. Anonymous callers get `401
  UNAUTHORIZED` **without** any paid/compute work happening.
- **ASR resource cap (M1).** New config `ASR_MAX_UPLOAD_BYTES` (default
  10 MB, overridable via env). The transcribe route rejects an oversized audio
  field with `413 PAYLOAD_TOO_LARGE` **before** reading it into the model. The
  global 26 MB `MAX_CONTENT_LENGTH` remains the outer bound; this is a tighter,
  ASR-specific inner bound.
- **Rate limiting (M1).** Add `/api/speaking/transcribe` to `ratelimit.py`'s rule
  table at a tighter limit (12/min per client) than the global default.
  `/api/speaking/roleplay` already has a rule (30/min); no change there.

## Non-goals
- No change to the anonymous-first UX: the journey still establishes a session at
  onboarding, so authenticated users hit these endpoints normally. (Verified: the
  frontend calls roleplay/transcribe/evaluate only after onboarding/login.)
- No true audio-duration metering (would require decoding first); the byte cap +
  rate limit are the resource guard.
- Register enumeration (L5) and Google `email_verified` (L5) are out of scope for
  this batch.

## Testing (TDD, pytest)
Write failing tests first, then implement:
1. `roleplay` / `transcribe` with **no session** → `401`; with a signed-in session → `200` (stub gateway / monkeypatched ASR).
2. **Auth-before-work proof:** inject a gateway whose `.score()`/`.generate()` raises if called; an **unauth** request to `writing/evaluate`, `speaking/evaluate`, `speaking/roleplay`, `placement/submit` returns `401` **without** the gateway being invoked (assert not called).
3. `transcribe` oversized audio (> `ASR_MAX_UPLOAD_BYTES`) → `413`; within cap → proceeds.
4. Rate-limit rule unit: `rule_for("/api/speaking/transcribe")` returns the tighter limit.
5. Full suite stays green (168 → +new). Existing authed tests (`client_with_seed`) unaffected.

## Boundary
Batch 1 is auth/resource hardening on 3 route files + ratelimit + config only. It
does not touch data scoping, schemas, or the frontend. Subsequent batches (a11y
H2/H3/M3, quality/i18n L-items) follow their own spec+plan.

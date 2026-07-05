# Security Batch 1 — LLM/ASR endpoint auth hardening — 2026-07-05

Closes audit findings **H1, M1, M2** (see `docs/superpowers/specs/2026-07-05-security-llm-asr-auth-hardening.md`).
TDD: failing tests written first, then implementation.

## What changed (files)
- `api/app/routes/speaking.py` —
  - **H1**: `speaking_roleplay` now calls `_require_uid()` first (was fully unauthenticated → paid LLM).
  - **M2**: `speaking_evaluate` gates `_require_uid()` at the top and reuses the uid in `save_attempt` (was calling the paid LLM before the auth check).
  - **M1**: `speaking_transcribe` now `_require_uid()` first + rejects audio larger than `ASR_MAX_UPLOAD_BYTES` with `413` before invoking Whisper.
- `api/app/routes/writing.py` — **M2**: `writing_evaluate` gates `_require_uid()` before `compute_metrics()` (spaCy) and the paid LLM; reuses uid in `save_attempt`.
- `api/app/config.py` — new `ASR_MAX_UPLOAD_BYTES` (default 10 MB, env-overridable).
- `api/app/ratelimit.py` — added `("/api/speaking/transcribe", 12, 60)` (tighter than global; ASR is CPU-heavy).
- `api/tests/test_security_llm_auth.py` — **new** (8 tests): roleplay/transcribe require auth; evaluate does NOT call the gateway when unauth (ordering proof via a recording gateway stub); transcribe oversize → 413; transcribe rate rule = (12,60).

**Correction (verified during impl):** `placement/submit` was in the original M2 hypothesis but is already auth-first — `_gateway()` at line 38 is only a DI lookup; the paid `gateway.score()` calls run after `_require_uid()`. No change made. Plan updated to note this.

## Why
The prior security pass (commit `40e537c`) secured the `*/generate` endpoints but
missed `roleplay` (unauth paid LLM), `transcribe` (unauth CPU-heavy ASR), and the
evaluate handlers that ran the paid/heavy work *before* the auth gate.

## How to test / verify
- `cd api && .venv/Scripts/python -m pytest -q tests/test_security_llm_auth.py` → 8 passed.
- Full suite: `.venv/Scripts/python -m pytest -q` → all green (176 total).
- Manual: `POST /api/speaking/roleplay` (or `/transcribe`) with no session → `401`.

## Caveats / known limits
- Resource guard for ASR = byte cap + rate limit (no true audio-duration metering; that would require decoding first).
- Rate limiter remains in-process (per-worker) — see the prior hardening log.
- These endpoints are used only after onboarding/login establishes a session, so authenticated UX is unchanged (verified against the frontend flow).

## Commit
- Pending (working tree).

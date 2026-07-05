# Plan — LLM/ASR endpoint auth hardening (Batch 1)

Spec: `docs/superpowers/specs/2026-07-05-security-llm-asr-auth-hardening.md`
Method: TDD (red → green → refactor). Run `cd api && .venv/Scripts/python -m pytest -q` after each task.

## Constraints
- No schema change, no new dependency, no contract change for authenticated callers.
- `_require_uid()` must be the FIRST statement in each affected handler.
- Keep diffs small and reviewable; update the change-log at the end.

## Task 1 — Failing tests (red)
**File:** `api/tests/test_security_llm_auth.py` (new)
- [ ] `roleplay` no session → 401; with `client_with_seed` (authed) → 200.
- [ ] `transcribe` no session → 401 (monkeypatch `asr.transcribe` so it never loads a model).
- [ ] Auth-before-work: build an app with a gateway stub whose `.score()`/`.generate()` raises `AssertionError`; unauth POST to `writing/evaluate`, `speaking/evaluate`, `speaking/roleplay`, `placement/submit` → 401 and gateway NOT called.
- [ ] `transcribe` oversized body (> `ASR_MAX_UPLOAD_BYTES`, set small via override) → 413.
- [ ] `rule_for("/api/speaking/transcribe")` → `(12, 60)`.
- [ ] Run suite → these fail.

## Task 2 — H1: guard roleplay (green)
**File:** `api/app/routes/speaking.py`
- [ ] Add `_require_uid()` as the first line of `speaking_roleplay()`.

## Task 3 — M2: auth-first ordering
**Files:** `api/app/routes/writing.py`, `speaking.py`
- [ ] `writing_evaluate`: call `uid = _require_uid()` at top; reuse `uid` in `save_attempt` (drop the inline `_require_uid()`).
- [ ] `speaking_evaluate`: same pattern.
- [ ] ~~`placement_submit`~~ — **CORRECTION (verified):** already auth-first. `_gateway()` at line 38 is only a DI lookup; the paid `gateway.score()` calls (lines 52/57) run *after* `_require_uid()` (line 41). No change needed.

## Task 4 — M1: transcribe guard + resource cap
**Files:** `api/app/config.py`, `api/app/routes/speaking.py`, `api/app/ratelimit.py`
- [ ] `config.py`: add `ASR_MAX_UPLOAD_BYTES` (default `10 * 1024 * 1024`, env-overridable, override-aware like the others).
- [ ] `speaking_transcribe`: `_require_uid()` first; after fetching the file, reject `len(audio_bytes) > cfg.ASR_MAX_UPLOAD_BYTES` with `ApiError("PAYLOAD_TOO_LARGE", ..., 413)` before calling `asr.transcribe`.
- [ ] `ratelimit.py`: add `("/api/speaking/transcribe", 12, 60)` to the rule table (place before any broader prefix).

## Task 5 — Green + regression
- [ ] Run `.venv/Scripts/python -m pytest -q` → all green (existing 168 + new).
- [ ] Confirm no existing test regressed (esp. `test_roleplay.py`, `test_routes_skills.py`, `test_placement_scoring.py`).

## Task 6 — Wrap up
- [ ] `bash tests/secret_scan.sh` (no bundle impact expected; sanity).
- [ ] Write `logs/security-llm-asr-auth_2026-07-05_log.md` (files, why, how to test, caveats, commit hash).
- [ ] Present diff summary; STOP for review. Do NOT merge/deploy.

## Risk / rollback
- Low: additive guards + reordering. If an authed flow breaks, the failing test
  pinpoints it; revert the single handler. No data migration to undo.

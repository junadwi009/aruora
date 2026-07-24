# Test-phase feedback gate + token efficiency — 2026-07-25

## What changed

**Feature A — 7h one-time feedback gate**
- New DB tables `test_gate` (per-user lock state, `unlocked_at`) and `feedback`
  (star rating 1-5 + free-text insight, min 20 chars).
- Focus-aware heartbeat: the client only accumulates active-time while the tab
  is visible **and** focused (`web/src/components/gate/useGateHeartbeat` wired
  via `FeedbackGate.tsx`); heartbeat ticks are clamped to 2x the poll interval
  so a suspended/backgrounded tab can't fast-forward the lock.
- After 7h of true active time, the UI shows a blocking modal
  (`web/src/components/gate/FeedbackGate.tsx`) requiring a star rating + a
  ≥20-character insight before the app unlocks again.
- Admins (per `ADMIN_EMAILS`) are exempt from the gate entirely.
- New endpoints in `api/app/routes/feedback.py`: gate status/heartbeat/unlock
  for the end user, plus `GET /api/admin/feedback` (admin-only) to review
  submitted feedback. Feedback submission also emails the admin address.

**Feature B1 — pool-freeze on the generate endpoints (latent safeguard)**
- `serve_or_generate` helper freezes the `GeneratedSet` pool at 7 sets per
  band on `POST /api/reading/generate` and `POST /api/listening/generate`:
  once 7 sets exist for a level, further calls serve a random existing set
  instead of paying for a new LLM generation.
- **This path is not currently exercised by the UI** — see Caveat 1.

**Feature B2 — per-user daily generation cap**
- `api/app/routes/_gencap.py` adds a `DAILY_GEN_CAP` (default 20, configurable
  via env) enforced per user per UTC day on `POST /api/vocab/generate`,
  `POST /api/lesson/generate`, and `POST /api/pronounce/generate`. The cap is
  only incremented on an actual LLM generation call (`note_generation`),
  never on a pool-serve, so pool hits are free and uncapped.
- Cap breach returns HTTP 429 with i18n key `gen.capReached`; the web client
  surfaces a friendly "come back tomorrow" notice instead of a raw error.

**Feature B3 — free default review model**
- `MODEL_SCORE` config default switched to the free OpenRouter model
  `deepseek/deepseek-chat-v3.1:free`. Override via env for higher-quality
  scoring if free-tier reliability/rate-limits become a problem.

**Feature C — Docker + env docs**
- Verified `docker compose up --build` still starts web/api/db cleanly with
  the new tables/migration applied.
- Documented the new env vars (`DAILY_GEN_CAP`, `GATE_LOCK_SECONDS`,
  `MODEL_SCORE`, etc.) in the README.

## Files

**New**
- `api/app/routes/feedback.py` — gate status/heartbeat/unlock + admin feedback listing endpoints
- `api/app/routes/_gencap.py` — shared daily-generation-cap decorator/helper
- `api/migrations/versions/e631087d0920_*.py` — adds `test_gate`, `feedback`, `gen_usage` tables
- `web/src/lib/gate.ts` — gate client state machine / heartbeat timing logic
- `web/src/components/gate/FeedbackGate.tsx` — blocking modal UI (rating + insight)

**Modified**
- `api/app/data/models.py` — `TestGate`, `Feedback`, `GenUsage` models
- `api/app/data/repository.py` (repo layer) — gate/feedback/gen-usage/pool methods
- `api/app/config.py` — gate + efficiency knobs (`DAILY_GEN_CAP`, `GATE_LOCK_SECONDS`, `MODEL_SCORE` default)
- `api/app/routes/reading.py`, `api/app/routes/listening.py` — pool-freeze (`serve_or_generate`) on `/generate`
- `api/app/routes/vocab.py`, `api/app/routes/lesson.py`, `api/app/routes/pronounce.py` — daily cap enforcement
- `api/app/__init__.py` — blueprint registration for `feedback`
- `web/src/lib/api/client.ts` — gate + feedback API methods
- `web/src/lib/i18n.tsx` — EN/ID strings for gate modal, cap-reached notice
- `web/src/App.tsx` — gate mounting/gating logic (admin exemption respected)
- `web/src/components/vocab/*`, `web/src/components/session/*` (Session), `web/src/components/pronounce/*` — cap-reached UX
- `README.md` — new env vars documented

## How to test

- Backend: `cd api && .venv/Scripts/python -m pytest -q`
- Web: `cd web && npm test && npx tsc --noEmit && npm run build`
- Demo the gate: set `GATE_LOCK_SECONDS=60` (instead of the real 7h) in the
  api env, log in as a non-admin, stay focused on the tab for 60s+ → the
  FeedbackGate modal should appear and block interaction until a rating +
  20-char insight is submitted.
- Demo the daily cap: set `DAILY_GEN_CAP=1`, generate a vocab list once
  (succeeds), generate again the same day → second call returns HTTP 429
  with i18n key `gen.capReached`, surfaced as a friendly notice in the UI.
- Demo the free model: override `MODEL_SCORE` to a paid model to compare
  scoring quality/reliability against the free default.

## Caveats (important)

1. **B1 pool-freeze is LATENT, not wired into the live UI path.** The
   Reading/Listening practice screens fetch via `GET /api/practice/set`,
   which serves a random set from the already-seeded `GeneratedSet` pool and
   never calls an LLM. The `POST /api/reading/generate` /
   `POST /api/listening/generate` endpoints that carry the 7-per-band
   pool-freeze logic are not called anywhere in the current frontend, so the
   freeze is a correct-but-inactive safeguard, not an active token saver.
   Per owner decision (2026-07-25), Reading/Listening intentionally stay
   pool-only (already zero-token per practice), so this is not being wired
   up further in this feature. The daily generation cap (B2) and the free
   default model (B3) are the efficiency changes that are actually live.
2. Free OpenRouter models are rate-limited and occasionally deprecated, and
   can return less reliable/parseable JSON than paid tiers. Writing/Speaking
   feedback quality is expected to be lower on the free model by design
   during the test phase; override `MODEL_SCORE` per-deployment if needed.
3. Gate active-time is focus-based (heartbeat only accumulates while the tab
   is visible and focused) and therefore approximate, not a precise wall-clock
   measurement. Heartbeat ticks are clamped to 2x the poll interval to bound
   drift from suspended tabs/laptops.
4. There is a minor lazy-create concurrency race on the first write to
   `test_gate` / `gen_usage` for a given user (two near-simultaneous requests
   could both attempt to create the row). Not a practical issue for the
   current single-user-per-account usage pattern; would need a proper
   upsert/unique-constraint guard before heavy concurrent multi-tab use.

## Regression results (2026-07-25)

- `api`: `pytest -q` → **198 passed**, 1 pre-existing benign collection
  warning (`PytestCollectionWarning: cannot collect test class 'TestGate'
  because it has a __init__ constructor`, from `tests/test_efficiency.py` —
  this is the `TestGate` SQLAlchemy model, not a pytest test class; expected).
- `web`: `npm test` → **68 passed** (27 test files), including
  `FeedbackGate.test.tsx` and `gate.test.ts`.
- `web`: `npx tsc --noEmit` → clean, no errors.
- `web`: `npm run build` → succeeded (pre-existing chunk-size-over-500kB
  warning on `index-*.js`, unrelated to this feature).
- `bash tests/secret_scan.sh` → `secret scan: clean — no API key found in
  web/dist`, exit 0.

## Commit hash

This commit (docs: update log for test-gate + token-efficiency), on branch
`feat/test-gate-token-efficiency`, built on top of Tasks 1-12
(`8074f34` .. `a61cb22`).

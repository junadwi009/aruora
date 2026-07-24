# Spec — Test-Phase Feedback Gate + Token-Efficiency Controls

**Date:** 2026-07-25
**Status:** Approved design → ready for implementation plan
**Scope:** Two features (A: usage lock/feedback gate; B: token-efficiency) + one
verification task (C: Docker). All changes respect the hard rules in `CLAUDE.md`
(update-log, i18n EN+ID, multi-user scoping, in-stack).

---

## 1. Motivation

The app is in a **test phase**. Two goals:

1. **Collect structured tester feedback** by pausing the app after a fixed amount
   of real use and requiring a rating + written insight before continuing.
2. **Cut LLM cost** while testing: stop regenerating practice content once a pool
   exists, cap generation per user per day, and move scoring/review to a free model.

Docker already exists (`docker-compose.yml`, `docker-compose.prod.yml`, `api/Dockerfile`,
`web/Dockerfile`, `web/Dockerfile.prod`), so "wrap into Docker" is reduced to
**verify + wire new env vars + document** — no new container topology.

---

## 2. Feature A — Test-Phase Feedback Gate

### 2.1 Behavior

- Each user accumulates **active in-app time**. At **7 hours cumulative** (`GATE_LOCK_SECONDS`,
  default `25200`), the app is blocked by a full-screen gate.
- The gate is cleared by submitting feedback: **1–5 star rating (required)** +
  **written insight (required, ≥ 20 characters)**.
- On submit: persist a `Feedback` row **and** email the admin (existing mailer;
  log-only fallback when SMTP unset).
- The gate is **one-time**: once `unlocked_at` is set, the app never locks again
  for that user.
- **Admins are exempt** (email in `ADMIN_EMAILS`) — they never see the gate.

### 2.2 Active-time accounting

- The SPA sends a heartbeat **only while the tab is focused** (visibilityState ===
  "visible" and window focused), every `GATE_HEARTBEAT_SEC` (default 60s).
- Each heartbeat increments the server-side counter by the elapsed interval,
  **clamped** to ≤ 2× the interval so a resumed-from-sleep tab can't jump the counter.
- Idle/background time is not counted (heartbeat pauses when tab hidden).

### 2.3 Data model

New table `test_gate` (one row per user, created lazily):

| column           | type              | notes                                  |
|------------------|-------------------|----------------------------------------|
| `user_id` (PK/FK)| int → user_profile| owner scope                            |
| `active_seconds` | int, default 0    | accumulated focused time               |
| `unlocked_at`    | datetime, null    | set when feedback submitted; null=locked-able |

New table `feedback`:

| column        | type              | notes                              |
|---------------|-------------------|------------------------------------|
| `id` (PK)     | int               |                                    |
| `user_id` (FK)| int → user_profile| owner scope                        |
| `stars`       | int (1–5)         | required                           |
| `insight`     | text              | required, ≥ 20 chars               |
| `created_at`  | datetime          | default now                        |

Alembic migration adds both tables. Repository gains ownership-scoped methods:
`gate_get(uid)`, `gate_add_seconds(uid, secs)`, `gate_unlock(uid)`,
`feedback_add(uid, stars, insight)`, `feedback_list()` (admin).

### 2.4 API — new blueprint `routes/feedback.py`

- `POST /api/gate/heartbeat` → `{ activeSeconds, locked, unlocked }`. Increments
  counter (clamped), returns current lock state. `_require_uid`. Admin → always
  `locked:false`.
- `GET  /api/gate/status` → `{ activeSeconds, thresholdSeconds, locked, unlocked, isAdmin }`.
- `POST /api/gate/unlock` → body `{ stars, insight }`. Validates (422 on bad
  stars / short insight), writes `Feedback`, sets `unlocked_at`, emails admin,
  returns `{ unlocked:true }`.
- `GET  /api/admin/feedback` → list all feedback (admin-only; reuse admin guard
  pattern from `routes/admin.py`).

`locked` rule: `unlocked_at is None AND active_seconds >= GATE_LOCK_SECONDS AND not isAdmin`.

### 2.5 Frontend

- New `web/src/lib/gate.ts`: starts/stops the focus-aware heartbeat, exposes gate
  state via a small hook/context.
- New `web/src/components/gate/FeedbackGate.tsx`: blocking full-screen modal with
  star picker + textarea + submit; disabled until valid; shows validation + submit
  errors. All strings via i18n (EN + ID).
- `App.tsx`: when `gate.locked` is true, render `<FeedbackGate>` over the app
  (route content not reachable). On successful unlock, resume normally.

### 2.6 Config (new env)

| var                   | default | meaning                             |
|-----------------------|---------|-------------------------------------|
| `GATE_ENABLED`        | `1`     | master switch (off = never locks)   |
| `GATE_LOCK_SECONDS`   | `25200` | 7 hours                             |
| `GATE_HEARTBEAT_SEC`  | `60`    | heartbeat interval                  |

---

## 3. Feature B — Token Efficiency

### 3.1 B1 — Serve-from-pool freeze (per skill+band, N = 7)

**Target:** Reading & Listening stop calling the generation LLM once **7 stored
sets exist for the requested band**.

- New repo method `count_sets(skill, band) -> int` and
  `add_set(skill, band, payload, source="generated")` (persist to existing
  `GeneratedSet`).
- `routes/reading.py` and `routes/listening.py` change from "always generate" to:
  1. If `count_sets(skill, band) >= POOL_TARGET` (default 7) → return
     `repo.serve_set(skill, band)` (random from pool). No LLM call.
  2. Else → `gateway.generate(...)`, then `repo.add_set(...)` to grow the pool,
     and return the fresh payload.
- **Level progression falls out naturally:** the pool is keyed by `band`. When a
  user's `SkillLevel` advances (e.g. B1 → B2), requests target a new band whose
  pool is empty → it fills to 7 for that band, then freezes again.
- `band` is taken from the request (as today), which reflects the user's current
  skill level. No schema change to `GeneratedSet`.

Env: `POOL_TARGET` (default `7`).

### 3.2 B2 — Per-user daily generation cap (backstop)

**Target:** A daily quota across **all** generation endpoints (reading, listening,
vocab, lessons, pronounce) — independent of, and in addition to, B1.

- New table `gen_usage` (`user_id`, `day` (date), `count`), unique on
  `(user_id, day)`. Repo: `gen_count_today(uid)`, `gen_incr_today(uid)`.
- Central enforcement helper `enforce_gen_cap(uid)` called at the top of each
  generation route (or wrapped once around `_gateway().generate` usage in the
  generation routes). When `gen_count_today(uid) >= DAILY_GEN_CAP`:
  - Reading/Listening → fall back to `serve_set` / `serve_any_set` if a pool
    exists; else raise a friendly `GEN_CAP_REACHED` (429) that the client renders
    as an i18n "daily limit reached, come back tomorrow" message.
  - Vocab/Lesson/Pronounce → raise `GEN_CAP_REACHED` (429).
- **Only successful generations count** (increment after a successful LLM call, or
  after a successful pool-fill in B1). Pure pool-serves (no LLM) do **not** count.
- Scoring/review calls (Writing/Speaking/Placement) are **not** capped — they are
  the point of the app and already cheap under B3.

Env: `DAILY_GEN_CAP` (default `20`). `0` = unlimited.

### 3.3 B3 — Free review model replaces Sonnet

- `config.py`: change `MODEL_SCORE` **default** from `anthropic/claude-sonnet-4-6`
  to a free OpenRouter model. Chosen default: **`deepseek/deepseek-chat-v3.1:free`**
  (strong instruction-following + reliable JSON). Remains env-overridable.
- `MODEL_GENERATE` stays `anthropic/claude-haiku-4-5` for the now-rare pool-fill
  generations.
- No code change to `LlmGateway._live_score` — it already reads
  `self._config.MODEL_SCORE`. Only the default changes.
- **Caveat (documented):** free OpenRouter models are rate-limited and can be
  deprecated. `MODEL_SCORE` override lets ops swap models without a code change.
  If JSON parsing failures rise, upgrade via env.

---

## 4. Feature C — Docker (verify + wire + document)

- Add all new env vars to `.env.example` with comments:
  `GATE_ENABLED`, `GATE_LOCK_SECONDS`, `GATE_HEARTBEAT_SEC`, `POOL_TARGET`,
  `DAILY_GEN_CAP` (and confirm `MODEL_SCORE` documented as free-by-default).
- Confirm both compose files pass `.env` through to `api` (already via `env_file`)
  — new vars need no compose edits, but verify.
- `docker compose up --build` boots db + api + web cleanly; migration runs.
- README: short "Test-phase gate + efficiency knobs" section listing the env vars
  and how to disable the gate (`GATE_ENABLED=0`) / raise the cap for a demo.

---

## 5. Cross-cutting requirements

- **i18n:** every new user-facing string (gate modal, star labels, feedback form,
  validation, cap-reached message) added to the EN + ID dictionaries in
  `web/src/lib/i18n.tsx`. No hardcoded UI strings.
- **Multi-user scoping:** `test_gate`, `feedback`, `gen_usage` all keyed by
  `user_id`; every repo method filters by owner. Admin-only endpoints guarded by
  the `ADMIN_EMAILS` allow-list pattern.
- **Update-log:** on each meaningful change, write
  `logs/{feature}_{YYYY-MM-DD}_log.md` (what/why/how-to-test/caveats/commit hash).
- **Migrations:** one Alembic revision adding `test_gate`, `feedback`, `gen_usage`.

---

## 6. Testing

**API (pytest):**
- Gate: heartbeat accumulates + clamps; locks at threshold; admin never locks;
  unlock validates stars/insight, writes feedback, sets `unlocked_at`, is idempotent
  (stays unlocked after threshold). Ownership: user A can't read/affect B's gate.
- B1: below target → generates + grows pool + counts; at target → serves pool, no
  LLM call (assert gateway not invoked); new band re-enters generate path.
- B2: cap reached → reading/listening fall back to pool or 429; vocab/lesson/pronounce
  429; pure pool-serve doesn't increment; scoring never capped; per-user isolation.
- B3: `MODEL_SCORE` default is the free model; override via env respected.

**Web:** Vitest for the gate hook (focus-aware heartbeat pauses when hidden) and
FeedbackGate validation; `npx tsc --noEmit`. Optional Playwright e2e: forced-lock
→ submit feedback → app resumes.

**Manual/Docker:** `docker compose up --build`; set `GATE_LOCK_SECONDS=60` to see
the gate quickly; submit feedback; confirm admin email/log + admin feedback list.

---

## 7. Out of scope

- Multi-dimension ratings (single star + insight only).
- Recurring/repeating gate (one-time only).
- Capping or changing Writing/Speaking scoring quality beyond the model swap.
- Any new container/service; changing prod deploy topology.

---

## 8. Defaults chosen (env-overridable)

| knob                | default                         |
|---------------------|---------------------------------|
| `GATE_LOCK_SECONDS` | `25200` (7h)                    |
| `GATE_HEARTBEAT_SEC`| `60`                            |
| `POOL_TARGET`       | `7`                             |
| `DAILY_GEN_CAP`     | `20`                            |
| `MODEL_SCORE`       | `deepseek/deepseek-chat-v3.1:free` |

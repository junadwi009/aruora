# persistence-progress-analytics — 2026-06-29

Phase 2c: persist Writing & Speaking evaluations and turn the Progress tab from a placeholder into a real dashboard (band-trend chart + clickable history that re-opens the saved feedback). Activates the previously-idle `attempts` table — **no schema change**.

## What changed
- **`api/app/data/repositories.py`** — `save_attempt(type,task,prompt,body,bands,criteria,cefr,metrics)->int`, `list_attempts(type=None)` (newest-first summaries), `get_attempt(id)` (full re-renderable payload; flattens the stored `criteria` JSON back into the dict so the client renders identically), `trends()` (per-skill time series, oldest-first). Column reuse: `bands` JSON holds the criteria dict **incl. `overall`**; `criteria` JSON holds the feedback payload (corrections/rewrite for writing, feedback/modelAnswer for speaking).
- **`api/app/routes/writing.py` + `speaking.py`** — after scoring, call `repo.save_attempt(...)` and add `savedId` to the response (purely additive; existing fields and the stub flag untouched).
- **`api/app/routes/history.py`** (new) + **`__init__.py`** — `GET /api/history/attempts?type=`, `GET /api/history/attempt/<id>` (404 if missing), `GET /api/stats/trends`.
- **`web/src/lib/api/client.ts` + `types.ts`** — `statsTrends` / `historyAttempts` / `historyAttempt` + `AttemptSummary` / `TrendPoint` / `Trends` / `AttemptDetail` types.
- **`web/src/components/progress/Progress.tsx`** — fetches trends + history on open; Recharts `LineChart` of Writing & Speaking overall (0–9, `connectNulls`, with an `sr-only` data-table mirror for a11y); newest-first history list; clicking a row loads the detail and opens a `Dialog` that re-renders the saved feedback via the **existing** skill renderers. Empty-state preserved when there's no data; loading state added.
- **`web/src/components/writing/Writing.tsx` + `speaking/Speaking.tsx`** — exported `FeedbackView` / `SpeakingFeedback`; made their revise/retry callback **optional** so the history Dialog renders them read-only.

## Decisions
- **No schema migration.** The `attempts` table was defined in Phase 1 but never written; 2c just starts using it. Reusing `bands`/`criteria`/`metrics` JSON columns avoids an Alembic revision.
- **Persist the full payload, not just bands.** Storing the feedback fields means "open past attempt" re-renders the *exact* feedback with the same components — no re-call to the LLM, no drift.
- **Additive routes.** `savedId` is added to evaluate responses; nothing else changes, so existing clients/tests stay green.
- **Scope held to Writing/Speaking.** Mock Test (L/R, `mocks` table) and Reading/Listening practice persistence are deferred to Phase 2d (different data paths). See spec.

## How to verify
- Unit: `cd api && .venv/Scripts/python -m pytest -q` → **73 passed** (8 new: 3 repo + 5 routes/history). `cd web && npm test` → **16 passed** (new client test); `npx tsc --noEmit` clean; `npm run build` OK.
- Live (container, `LLM_MODE=live`): one Writing + one Speaking eval both returned `savedId` (1, 2) with real Sonnet bands + metrics. Then:
  - `GET /api/stats/trends` → `{writing:[{overall:4.5,...}], speaking:[{overall:5.0,...}]}` grouped per skill, chronological.
  - `GET /api/history/attempts` → newest-first `[{id,type,task,cefr,overall,createdAt}]`.
  - `GET /api/history/attempt/1` → full payload (keys: bands, body, cefr, corrections, createdAt, id, metrics, modelAnswer, prompt, rewrite, task, type).
  - `GET /api/history/attempt/999` → `404`.

## Caveats / known limits
- The live writing scorer sometimes also returns a `modelAnswer` field; it's stored and harmless (the writing renderer ignores it).
- Two real sample attempts now live in the dev Postgres volume from the live verification — there's no delete endpoint yet, so they'll show in Progress until the volume is reset. Fine as demo data.
- Chart x-axis uses local `MM/DD HH:mm` labels; with many attempts on one day labels can crowd (acceptable for a single-user app). No per-criterion toggle yet — only overall per skill.
- Trends/history are global (single-user app); `attempts` intentionally has no `user_id`.

## Commits
- `4514bba` docs(spec): Phase 2c design
- `4f6bc44` feat(api): persist attempts + history & trends endpoints
- `7462e79` feat(web): Progress tab — trends + clickable history

# guided-lessons — 2026-06-29

Phase 2d-1: a guided **Teach → Practice → Produce → Review** session, launched from Home's "Start". First slice of the 2d basket. Wires the already-authored `lesson` prompt + the idle `lessons` table to a route + a session-runner UI. No schema change.

## What changed
### Backend
- **`api/app/domain/lesson_plan.py`** (new, pure) — `pick_focus(skill_levels)` = weakest skill (lowest CEFR band; ties broken by plan weight `writing > listening > speaking > reading`; default `writing`); `current_day(start_date, length_days, today)` = `clamp(days_since_start + 1, 1, length)` (1 if no program).
- **`api/app/data/repositories.py`** — `get_lesson(day)` / `save_lesson(day, lesson, focus)` (upsert by the `day` PK).
- **`api/app/routes/lesson.py`** (new) + `__init__.py` — `GET /api/lesson/today` (computes day/focus/band, returns cached lesson or null), `POST /api/lesson/generate {day?,focus?,band?,force?}` (cache-or-generate via `gateway.generate("lesson", …)`, idempotent without `force`), `GET /api/lesson/<int:day>`.
- **`fixtures/stub_responses.json`** — 4 offline lesson stubs `lesson:{writing|listening|speaking|reading}:B1` (band-fallback covers other bands). **`fixtures/seed_lesson.json`** + `seed.py` — a Day-1 writing lesson seeded at boot so "Today" works zero-API on a fresh DB.

### Frontend
- **`web/src/lib/api/client.ts` + `types.ts`** — `lessonToday` / `lessonGenerate` / `lesson(day)` + `Lesson` / `LessonToday` types.
- **`web/src/components/session/Session.tsx`** (new) + registered `"session"` in `AppShell` — Teach (explanation + examples) → Practice (per-item auto-check with immediate feedback) → Produce (hands off to the skill tab) → Review (collocations + tip), with a stage stepper, a Generate CTA when uncached, and a Regenerate (force) button.
- **`web/src/components/menu/viewContext.tsx`** — added `"session"` view + a one-shot prefill: `goWithPrefill(skill, text)` / `consumePrefill(skill)`.
- **`Writing.tsx` / `Speaking.tsx`** — consume the prefill on mount (Writing → essay box, Speaking → cue-card question). **`Home.tsx`** — "Start" now opens the session.

## Decisions
- **Focus = weakest skill, not a fixed day-list.** v3 has no 30-day day-by-day plan (only milestones), so today's lesson targets the lowest-band skill — directly serving "lift the weak skills." Day number comes from the active program (or 1).
- **Cache per day in `lessons`.** First generate is slow (live 20-60s); re-opening is instant. `force` regenerates (Regenerate button).
- **Speaking prefill = cue question, not transcript.** The Produce handoff sets the Part-2 cue; the learner still records/types their own answer. Writing prefill = the essay starter.

## How to verify
- Unit: `cd api && .venv/Scripts/python -m pytest -q` → **84 passed** (11 new: 6 lesson_plan + 1 repo + 4 routes). `cd web && npm test` → **20 passed** (3 Session smoke + 1 client). `npx tsc --noEmit` clean; `npm run build` OK.
- Live (container, `LLM_MODE=live`):
  - `POST /api/lesson/generate {}` → full lesson (goal/teach/exercises×3/produce/review) from the live model.
  - `GET /api/lesson/today` → now returns the cached lesson.
  - `POST /api/lesson/generate {day:1}` (no force) → returns the cached one (idempotent).
  - `GET /api/lesson/1` → cached; `GET /api/lesson/9` → `{lesson:null}`.

## Caveats / known limits
- The existing dev Postgres volume predates the Day-1 seed (seed_all is idempotent on `placement_combos`), so `today` started as `lesson:null` there until first generate — the seed path is exercised on a fresh DB (covered by unit tests).
- This slice **runs** a session but does not yet mark it "complete" / tick plan-day progress — deferred to a later 2d slice.
- Auto-check compares trimmed/lowercased exact strings — fine for gap-fill/MCQ; open-ended rewrite items grade leniently (exact match only).
- Lessons are practice, not graded; no band is produced by a session.

## Commits
- `7a62938` docs(spec): Phase 2d-1 design
- `6d73255` feat(api): lesson routes + planner + Day-1 seed
- `2370a16` feat(web): guided-session runner + lesson client + prefill handoff

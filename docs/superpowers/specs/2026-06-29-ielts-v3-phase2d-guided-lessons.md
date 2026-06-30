# IELTS Coach v3 — Phase 2d-1 Design: Guided Lessons

| | |
|---|---|
| **Status** | Approved (verbal) → implementation |
| **Date** | 2026-06-29 |
| **Phase** | 2d-1 (first slice of the 2d basket) |
| **Owner** | Arjuna D. Putranto |

## 1. Goal
A guided micro-lesson the learner runs from Home's "Today / Start": an evidence-based **Teach → Practice → Produce → Review** session. Turns the app from "tools + placement" into a coached daily loop. The `lesson` generation prompt and the `lessons` table already exist (idle) — this slice wires them to a route + a session-runner UI.

## 2. Scope
**In:** lesson generate/cache routes; today/focus/day computation; offline stub + Day-1 seed; a `Session` view (Teach → auto-checked exercises → Produce handoff → Review); Home "Start" → session; minimal cross-view prefill for the Produce handoff.
**Out (later 2d slices):** marking a session "complete" / ticking plan-day progress; a full 30-day day-by-day plan list; Mock Test; flashcards/vocab; pronunciation scoring. Tables `mocks`/`cards` stay idle.

## 3. Lesson shape (already defined in `prompts.py["lesson"]`)
```
{ goal, skill,
  warmup:{instruction,duration_minutes},
  teach:{explanation, examples[]},
  exercises:[ {type, instruction, items:[{prompt, answer, distractor?, feedback}]} ],
  produce:{instruction, prefill, duration_minutes},
  review:{collocations[], tip} }
```
Generation: `gateway.generate("lesson", skill=focus, band=band, day=, focus=, tasks=)`.
- Live: resolves `GENERATE_PROMPTS["lesson"]` (skill key miss → task fallback).
- Stub: key `lesson:{skill}:{band}` with band-fallback `lesson:{skill}:`.

## 4. Backend
- **`api/app/domain/lesson_plan.py`** (pure, tested): `pick_focus(skill_levels: list[(skill,band)]) -> skill` = lowest band; tie-break by plan weight order `[writing, listening, speaking, reading]`; default `writing` if empty. `current_day(program, today: date) -> int` = `clamp((today - start_date).days + 1, 1, length_days)`; `1` if no program.
- **`repositories.py`**: `get_lesson(day) -> dict|None` (returns `{day, focus, lesson, createdAt}`); `save_lesson(day, lesson, focus) -> None` (upsert by day PK).
- **`api/app/routes/lesson.py`** (new blueprint):
  - `GET /api/lesson/today` → `{day, focus, skill, band, lesson|null}`. Computes focus (pick_focus over skill_levels) + band (that skill's current band, default `B1`) + day (current_day over latest program). Returns the cached lesson for `day` if present, else `lesson:null`.
  - `POST /api/lesson/generate {day?, focus?, band?, force?}` → if a cached lesson exists for `day` and not `force`, return it; else `gateway.generate("lesson", ...)`, `save_lesson`, return `{day, focus, skill, band, lesson}`. Missing params default to today's.
  - `GET /api/lesson/<int:day>` → `{day, ...lesson}` or `{lesson:null}`.
- **Offline**: add `lesson:{writing|listening|speaking|reading}:B1` to `fixtures/stub_responses.json` (band-fallback covers other bands). **Seed Day-1**: `seed_all` inserts a Day-1 lesson (focus from a fixture) into `lessons` if empty, so "Today" shows a ready lesson with zero API on first run (matches the seed-content convention).
- Register blueprint in `__init__.py`.

## 5. Frontend
- **`client.ts` + `types.ts`**: `lessonToday()`, `lessonGenerate(body)`, `lesson(day)` + types `Lesson`, `LessonToday` (day/focus/skill/band/lesson).
- **`components/session/Session.tsx`** (new) + register `"session"` in `viewContext` `View` union and `AppShell` viewRegistry:
  - On open, `lessonToday()`. If `lesson` present → render it. If null → show a "Generate today's lesson" CTA → `lessonGenerate()` (loading state; live can take 20–60s) → render.
  - Stages: **Teach** (goal + explanation + examples) → **Exercises** (each item auto-checks on submit, shows `feedback` immediately, ~85% target) → **Produce** (instruction + "Open {skill}" button that navigates with prefill) → **Review** (collocations + tip). A simple stepper drives Teach→Exercises→Produce→Review.
- **Prefill handoff**: `viewContext` gains `prefill?: {skill, text}` + `goWithPrefill(skill, text)`. `Writing.tsx`/`Speaking.tsx` read+consume it once on mount (prefill the essay/transcript box). Produce "Open {skill}" calls `goWithPrefill`.
- **Home**: "Start" → `setView("session")`.

## 6. Testing (TDD)
- api: `lesson_plan` (pick_focus lowest+tiebreak; current_day clamp + no-program); repo get/save lesson (upsert); routes (today returns computed focus/day + seeded Day-1 lesson; generate caches and is idempotent w/o force; force regenerates; `/<day>` cached vs null); stub offline returns a lesson with `stub:true`.
- web: client method URLs; Session smoke (renders teach + exercises from a fixture lesson; answering an exercise reveals feedback; Produce button calls goWithPrefill).
- Honesty: lessons are practice, not graded.

## 7. Boundaries
Lesson routes are the producer; Session is the consumer. The only cross-cutting addition is `prefill` in viewContext (one field + one setter). Day/focus logic is isolated in `lesson_plan.py` and pure. No schema change (the `lessons` table already exists).

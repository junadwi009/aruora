# persist-practice-rl — 2026-06-29

Phase 2d-5: Reading/Listening practice scores now persist and show as trend lines on Progress (previously only Writing/Speaking + mocks were tracked).

## What changed
- **api**: `POST /api/practice/attempt {skill,band,correct,total}` (reading|listening only) saves to `attempts` (bands.overall=band, metrics={correct,total}); `repo.trends()` now buckets all four skills.
- **web**: client `practiceAttempt`; `QuizRunner` posts the score on submit (fire-and-forget, percent→`bandFromPct`). `Progress` chart gains Reading + Listening lines; the clickable history list is filtered to writing/speaking (only those re-open feedback).

## Decisions
- Reuse `attempts` (no new table) with type=reading|listening; client sends the approx band (computed via the shared `bandFromPct`).
- R/L attempts feed trends only, not the clickable history (no examiner feedback to re-render).

## Verify
- api `pytest -q` → 96 passed (+1). web `npm test` → 35 passed (+1); tsc clean; build OK.
- Live: `POST /api/practice/attempt {reading,7.0,9/10}` → savedId; `GET /api/stats/trends` → keys writing/speaking/reading/listening, reading point overall 7.0.

## Caveats
- Band from percent is the same coarse estimate as the mock; labelled as such.
- The Progress sr-only a11y table still mirrors Writing/Speaking only (chart shows all four).

## Commits
- `3d95039` feat(progress): persist Reading/Listening practice → 4-skill trends

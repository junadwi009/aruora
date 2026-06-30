# mock-test — 2026-06-29

Phase 2d-2: the **Test** tab now runs a Listening + Reading mock, scores it to approximate bands, persists to the idle `mocks` table, and shows it on Progress.

## What changed
- **api**: `repositories.py` `save_mock`/`list_mocks`; `routes/mocks.py` `POST /api/mocks {listening,reading,overall}` → `{id}`, `GET /api/mocks` (newest-first). Registered. No schema change.
- **web**: `lib/band.ts` `bandFromPct` (piecewise approx) + `roundHalf`; client `mocksList`/`mockSave` + `MockScore` type; `components/test/MockTest.tsx` (replaces the "coming soon" placeholder) — intro → Listening section → Reading section under one 30-min `Timer` → result (L/R/overall) → auto-save → CTA to Progress. `Progress.tsx` adds a Mock-tests history section.

## Decisions
- Reuses `practiceSet` (generated_sets) for the L/R content — no new generation. Grades locally like QuizRunner.
- Band from percent is a **coarse estimate** (sets are far shorter than a 40-Q paper); labelled as such, not an official conversion.
- Overall = round-half of the L/R band mean.

## Verify
- api `pytest -q` → 86 passed (+2). web `npm test` → 25 passed (+5: band×3, client, MockTest smoke); tsc clean; build OK.
- Live: `POST /api/mocks {6.0,7.0,6.5}` → `{id:1}`; `GET /api/mocks` → the row with createdAt. Renders in Progress under "Mock tests".

## Caveats
- Listening "audio" is browser TTS of the transcript (offline stand-in), same as practice.
- No per-section timer (one shared 30-min countdown); auto-submits/scoring on expiry.
- `cards` table still idle (flashcards = 2d-4).

## Commits
- `3c74419` feat(mock): Listening+Reading mock test, scored + persisted

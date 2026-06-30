# flashcards-vocab — 2026-06-29

Phase 2d-4: topic **Vocabulary** generation + **SM-2 flashcards**. Activates the last idle content table (`cards`).

## What changed
- **api**: `domain/sm2.py` pure SM-2 `schedule(...)`. Repo card ops (`add_card`/`add_cards`/`list_cards`/`card_stats`/`due_cards`/`review_card`/`delete_card`) with tz-safe (naive-UTC) due comparisons for SQLite+Postgres. `routes/cards.py` (GET /api/cards +stats, GET /api/cards/due, POST /api/cards single|batch, POST /api/cards/<id>/review, DELETE /api/cards/<id>) + `routes/vocab.py` (POST /api/vocab → gateway vocab gen) + offline `generate:vocab:B1` stub. Registered. No schema change.
- **web**: client `vocab`/`cardsList`/`cardsDue`/`cardAdd`/`cardReview`/`cardDelete` + types. `components/vocab/Vocab.tsx` — Build (topic → 15 words → Add one/all) + Review (flip → Again/Hard/Good/Easy = q 1/3/4/5 → reschedule), deck stats header. New `vocab` view; Home "Vocab" link.

## Decisions
- SM-2 standard: q<3 lapses (reps→0, interval→1, lapses+1); reps 0→1d, 1→6d, else round(interval·ease); ease floored 1.3. UI grades map to quality 1/3/4/5.
- Card back = definition + example (built from the vocab word) so a generated word becomes a usable card in one click.
- Due filtering done in Python (tz-normalised) — decks are single-user/small; avoids SQLite naive/aware comparison pitfalls.

## Verify
- api `pytest -q` → 95 passed (+7: sm2×3, repo cards×2, routes×2). web `npm test` → 34 passed (+3: client, vocab×2); tsc clean; build OK.
- Live: add card → `id:1`; stats total/due 1; due list 1; review Good → reps 1, interval 1, due +1 day; `POST /api/vocab {technology,B2}` → 15 words.

## Caveats
- No edit-card or per-deck grouping; one flat deck. No "leech" handling beyond lapse count.
- Vocab generation is live-only for fresh topics (offline stub covers `environment`/B1 + band-fallback).

## Commits
- `ca80edd` feat(vocab): topic vocabulary + SM-2 flashcards

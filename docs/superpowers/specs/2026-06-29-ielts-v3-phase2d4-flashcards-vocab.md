# Phase 2d-4 Design: Vocabulary + SM-2 Flashcards

**Status:** approved (batch) → implementation · **Date:** 2026-06-29

## Goal
Activate the idle `cards` table: generate topic vocabulary, add words to a deck, and review them with SM-2 spaced repetition (flip → grade → reschedule).

## Backend (TDD)
- `domain/sm2.py`: pure `schedule(ease, interval, reps, lapses, quality) -> {ease, interval, reps, lapses}` (SM-2; q<3 resets reps + interval=1 + lapses+1; ease clamped ≥1.3; reps 0→1d, 1→6d, else round(interval*ease)).
- Repo (`cards`): `add_card(front, back)->int`, `add_cards(items)->int` (count), `list_cards()`, `card_stats()->{total,due}`, `due_cards(now)`, `review_card(id, quality, now)->dict|None` (applies sm2, sets due=now+interval days), `delete_card(id)->bool`.
- `routes/cards.py`: `GET /api/cards` (+stats), `GET /api/cards/due`, `POST /api/cards` (single `{front,back}` or `{cards:[...]}`), `POST /api/cards/<id>/review {quality}`, `DELETE /api/cards/<id>`.
- `routes/vocab.py`: `POST /api/vocab {topic, level?}` → `generate("generate", skill="vocab", band=level)`. Stub `generate:vocab:B1`.
- Register blueprints. No schema change (`cards` exists).

## Frontend (TDD)
- client: `vocab(body)`, `cardsList`, `cardsDue`, `cardAdd(body)`, `cardReview(id,quality)`, `cardDelete(id)` + `Card`/`VocabSet` types.
- `components/vocab/Vocab.tsx` (+ `vocab` view, Home link): two modes — **Build** (topic → generate 15 words → "Add word"/"Add all" to deck) and **Review** (due count → flip card → Again/Hard/Good/Easy = quality 1/3/4/5 → `cardReview` → next). Deck stats header.

## Testing
api: sm2 vectors (good progression 1→6→round; again resets); repo add/list/due/review/delete + stats; routes incl. review reschedules, delete 200/404, vocab stub. web: client URLs; Vocab smoke (Build renders, generate lists words; Review shows empty/flip).

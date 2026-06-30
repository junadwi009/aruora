# multiuser-scoping — 2026-06-29

Phase 3b: scope **all** user data per account so registered users can't see each other's data. The security-critical slice of the accounts epic.

## What changed
- **Schema:** `attempts`/`mocks`/`cards` gain `user_id` (FK, indexed); `lessons` become a composite PK `(user_id, day)` — per-user lessons.
- **Repository:** every data method now takes `user_id` and filters by it: `save_attempt`/`list_attempts`/`get_attempt`/`trends`, `save_mock`/`list_mocks`, `add_card`/`add_cards`/`list_cards`/`card_stats`/`due_cards`/`review_card`/`delete_card`, `get_lesson`/`save_lesson`. Ownership-checked reads/mutations (`get_attempt`/`review_card`/`delete_card`) return `None`/`False` when the row belongs to another user.
- **Routes:** `_deps.py` gains `_uid()` (session uid or None) + `_require_uid()` (401 if absent). Writes (`writing|speaking|practice/attempt`, `mocks` POST, `cards` POST/review/delete, `lesson/generate`) require a session user; reads (`history`, `stats/trends`, `mocks` GET, `cards` GET, `lesson/today|<day>`, `skill-levels`, `program/milestones`) return empty for anonymous. `onboarding` now establishes the session; `placement/submit`, `program`, `skill-levels`, `lesson` resolve the user by session id, not "most recent".
- **Seed:** dropped the global Day-1 lesson seed (lessons are per-user, generated on demand).

## Tests
- New `test_attempts_are_isolated_per_user` + per-table isolation assertions (mocks/cards/lessons): user B's listings are empty, B can't `get_attempt`/`review_card`/`delete_card` A's rows. Repo tests rethreaded with `user_id`; `conftest` registers a session user so route tests are scoped. api **105 passed**.

## Verify (live, recreated DB)
- A registers → saves a card → A sees 1. B registers → B sees **0** cards. B `DELETE /api/cards/1` (A's card) → **404**. A still has the card. Isolation holds end-to-end.

## Caveats
- Schema via `create_all` → recreated the dev volume (throwaway data wiped). Incremental Alembic migrations still documented debt — they'll matter to preserve data on a populated prod DB across these column adds.
- Lessons no longer pre-seeded → "Today" shows a Generate CTA on first run per user (expected).
- Account flow still isn't visible in the journey until **3c** wires Login/Register.

## Commit
- `6178e66` feat(api): scope all user data per-account (multi-user)

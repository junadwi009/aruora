# settings-hub-milestones — 2026-06-29

Phase 3d + 3e: milestone editing and a full Settings hub (profile + photo, change password, help). Completes the Phase 3 accounts epic.

## 3d — Milestone CRUD
- `get_milestones` now returns `id`. Ownership-scoped repo methods `add_milestone`/`update_milestone`/`delete_milestone` (milestone → program → user_id; cross-user or no-program → None/False). Routes `POST/PUT/DELETE /api/program/milestones[/<id>]` (404 on cross-user / missing).
- web: `MilestonesSection` in Settings — edit title, day target, per-skill target band (selects), add/delete rows. client `milestoneAdd/Update/Delete`.

## 3e — Settings hub
- `user_profile` += `country`/`exam_date`/`bio`/`avatar`. Repo `update_profile`/`set_avatar`/`change_password` (verify current → re-hash). Routes `PATCH /api/account/profile`, `POST /api/account/avatar` (image data URL, ~2 MB cap, 422 otherwise), `POST /api/account/password` (401 wrong current, 422 short). `/me` returns the new fields.
- web sections: `ProfileSection` (name/country/exam date/notes + avatar upload via FileReader→dataURL, 2 MB guard), `SecuritySection` (change password, gated on having an account), `HelpSection` (FAQ accordion: placement, "estimate" honesty, ASR approximation, data privacy, offline). Settings now composes Appearance · Profile · Security · Milestones · Help · Sign out.

## Verify
- api `pytest -q` → 113 passed (+8: 4 milestone CRUD + 4 profile). web `npm test` → 46; tsc clean; build OK.
- Live (recreated DB for the new columns): profile PATCH saves name/country/examDate; avatar image → 200, non-image → 422; change password wrong-current → 401, correct → 200; milestone PUT/add → 200.

## Caveats
- Avatar stored as a base64 data URL in the DB row (simple, single-host; not a CDN). 2 MB cap.
- Schema via `create_all` → dev volume recreated again (throwaway data). Incremental Alembic migrations still the documented debt to preserve a populated prod DB.
- Settings tab is desktop-sidebar reachable; mobile via the sidebar too (no bottom-tab slot).

## Commits
- `735176a` feat(api): milestone CRUD + profile/avatar/password endpoints
- `69de194` feat(web): Settings hub — profile+photo, security, milestones editor, help

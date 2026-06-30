# settings-extras-i18n — 2026-06-29

Phase 4a: exam countdown, per-skill targets, data export + account deletion, and an in-house ID/EN i18n with a language toggle.

## What changed
- **Targets + countdown** (`608f8bc`): profile PATCH accepts `targetBand` + `skillTargets`; `/me` returns `skillTargets`. Settings `TargetsSection` (overall band + per-skill CEFR). Home shows an **exam countdown** computed from the stored `exam_date`.
- **Data & privacy** (`608f8bc`): repo `export_data` (profile + attempts/mocks/cards/lessons/programs/milestones/skill-levels/placement) and `delete_account` (deletes every owned row, scoped, clears session). Routes `GET /api/account/export`, `DELETE /api/account`. Settings `DataSection` (download JSON; delete with a confirm step).
- **i18n** (`032f52b`): `lib/i18n.tsx` — `I18nProvider` + `useT().t(key)` with EN→key fallback, language persisted in localStorage, applied at boot. Translated the high-visibility surfaces (Sidebar + BottomTabs nav, Welcome, Settings section labels + theme/sign-out) and added a **Language** toggle (English/Indonesia). `useT` returns an English fallback outside the provider so tests need no wrapper.

## Verify
- api `pytest -q` → 119 passed (+5: targets, export, delete). web `npm test` → 49 (i18n×2 + existing); tsc clean; build OK.
- Live (earlier this session): profile/targets PATCH, export JSON, delete account all behaved; countdown renders from exam date.

## Caveats
- **i18n coverage is a starter set** — nav, Welcome, and Settings labels translate; the rest of the app stays English until migrated through the same dictionary. The toggle works and persists.
- Data export is a single JSON blob (datetimes ISO-encoded); avatar base64 is included, so the file can be large.
- Account deletion is immediate and irreversible (a confirm step guards it); no soft-delete/grace period.

## Commits
- `608f8bc` feat(4a): exam countdown, per-skill targets, data export + account delete
- `032f52b` feat(4a): in-house i18n (ID/EN) — language toggle + core surfaces

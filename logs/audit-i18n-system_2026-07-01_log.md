# audit-i18n-system — 2026-07-01

Owner asked to default the criteria card collapsed, then continue the deferred
language + system audit.

## 1. Criteria card default collapsed (`70634ce`)
`TipsSidePanel` — `criteriaOpen` now defaults to `false`, so the self-assessment
card starts collapsed (header + chevron only) and expands on click.

## 2. Language audit
### Findings
- **i18n key parity: clean** — EN and ID dictionaries were already equal (401=401)
  with no missing `t()` keys before this pass.
- **Long-tail gaps found** (hardcoded English still not wrapped in `t()`): the
  Settings sub-sections (Profile / Security / Reminders / Targets / Data /
  Milestones / Help), the font picker + "Signed in" in `Settings.tsx`, the auth
  screens (placeholders, aria-labels, error/reset messages), `Results.tsx`, and
  generic UI aria-labels (Dialog / Toast / StepIndicator).

### Fix (`f5d153c`)
- Two parallel subagents wrapped the strings with `t()` across those files
  (disjoint groups); a merge script spliced the keys into `i18n.tsx` centrally.
  Plus a hand pass for `Settings.tsx` (font section + "Signed in").
- ~80 new EN+ID keys. **Dictionary parity now 480 = 480, no missing `t()` keys.**
- Example values (`you@example.com`) and practice content stay as-is.

## 3. System audit
- **No TODO / FIXME / HACK / XXX** anywhere in `api/app` or `web/src`.
- **No stray `console.log` / `print(`** in source (grep matched only `Blueprint(`).
- **Alembic**: single authoritative baseline migration; schema owned by Alembic.
- **Remember-me** added earlier is session-only (no DB column, no migration).
- **Tests green**: api 143, web 55, e2e 5. `tsc` clean.
- **Secrets**: no key patterns in tracked diffs; `.env`/`.env.example` gitignored.

### Known remaining (not blocking; documented)
- A few deep skill-practice screens may still have minor English micro-copy — the
  automated `t()`-key scan is clean, but only strings that were literal-in-JSX are
  guaranteed covered; dynamically-built strings should be spot-checked over time.
- Deferred product items unchanged: per-user reminder timezone, Google OAuth
  wiring (`google_sub` column ready), true multi-turn roleplay scoring, go-live
  deploy (hosting + SMTP_/REMINDER_TOKEN/OPENROUTER_API_KEY).

## Verify
- `tsc` clean; `vitest run` → 55 passed; api `pytest` → 143 passed.
- Live (docker compose up --build web): logged in — Settings renders fully in
  Indonesian (Profil/Target/Keamanan/Pengingat/Data/Bantuan/Admin Utama + Font
  bacaan/Bawaan/Ramah disleksia/Sudah masuk); auth placeholder "Minimal 6
  karakter"; Tips criteria card starts collapsed (`aria-expanded=false`).

## Commits
- `70634ce` feat(tips): default the self-assessment criteria card to collapsed
- `f5d153c` feat(i18n): translate remaining chrome — Settings, auth, results, UI

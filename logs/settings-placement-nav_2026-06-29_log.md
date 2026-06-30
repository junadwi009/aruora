# settings-placement-nav — 2026-06-29

Phase 2e-4/5/6: the product-side audit fixes — Settings (theme + accessible fonts), placement ASR, and navigation/honesty polish.

## 2e-4 Settings: dark mode + dyslexia/hyperlegible fonts (`6e7f1a3`)
- `lib/settings.ts` persists theme + font in localStorage and applies them to `<html>` (the `.dark` class + `--font-ui`/`--font-reading` overrides). Applied at boot in `main.tsx`.
- `Settings` view replaces its placeholder: Light/Dark toggle, a 3-way font picker (Default · Dyslexia-friendly=OpenDyslexic · Hyperlegible=Atkinson), and a Lock (logout) when a passcode is set. This finally **uses** the four fonts that were bundled but unreachable.
- Removed the now-dead `Placeholder` in AppShell. Added a localStorage shim to `test-setup.ts`.

## 2e-5 Placement Speaking ASR (`554895c`)
- Replaced the placement Speaking "speech recording — coming soon" block with the live `Recorder` (2b-2): record → transcribe → appended into the editable transcript. Updated `PlacementIntro` copy. Placement now matches the Speaking tab + Pronounce.

## 2e-6 Nav + milestone + a11y (`a647920`)
- Sidebar surfaces **Pronounce** + **Vocab** (were Home-quick-link-only).
- Home's fake hardcoded **"30% milestone"** bar replaced with the **real** program milestones (`api.milestones` → title + day target), hidden when none.
- Progress `sr-only` data table now mirrors **all four** skills (was Writing/Speaking only).

## Verify
- web `npm test` → 42 passed (settings×4, Settings smoke, +mock updates). tsc clean; build OK.
- e2e (`npx playwright test`) → **4/4** against the rebuilt compose stack: load, →Vocabulary, →Mock Test, and **Settings dark-mode toggles `.dark` on `<html>`** (live browser).

## Caveats
- Mobile BottomTabs still a curated 5 (Pronounce/Vocab reachable via sidebar on desktop + Home quick links on mobile) — deliberate, to avoid crowding.
- Home milestones list has no completion ticks (no per-day/session completion tracking yet) — it shows targets, not progress.

## Commits
- `6e7f1a3` feat(settings) · `554895c` feat(placement) · `a647920` feat(nav) · `f0fdaff` test(e2e dark mode)

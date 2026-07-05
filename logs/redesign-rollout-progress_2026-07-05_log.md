# Redesign rollout — Progress screen (Batch 5.1) — 2026-07-05

First screen of the "Study Desk" identity rollout beyond shell + Home. Executes the
already-approved direction (spec: `docs/superpowers/specs/2026-07-05-redesign-shell-home.md`).

## What changed (files)
- `web/src/components/progress/Progress.tsx` —
  - Screen header promoted to the **display face**, larger (`text-xl font-bold`,
    `--font-display`) with roomier padding — matches the new Home hierarchy.
  - Section labels (Band trend / Mock tests / History) lifted from tiny all-caps muted
    micro-text to **`text-sm font-semibold` in text colour** — clearer editorial hierarchy.
  - No logic, data, chart, dialog, or i18n change. The hardened `Dialog` (Batch 2) and the
    a11y data-table mirror are untouched.

## Why
Progress used the old small header + all-caps-muted section labels; this aligns it with
the new identity so navigating from Home doesn't drop back to the previous look.

## How to test / verify
- `cd web && npx tsc --noEmit && npm test` → clean, 66 passed.
- Visual (owner's Chrome): open Progress — bigger display heading, warm canvas, clearer
  section headings; history dialog still opens/traps focus.

## Caveats
- Recharts line colours remain hardcoded skill hues (teal/amber/violet) — a later token
  pass could map them to the CEFR palette; left as-is (not identity-critical).
- Remaining screens (Reading/Listening/Writing/Speaking/Tips/Vocab/MockTest/Settings)
  still use their prior headers — next rollout steps.

## Commit
- `2accc7f` — Progress rollout. Not pushed.

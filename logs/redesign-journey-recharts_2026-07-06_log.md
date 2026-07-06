# Redesign Batch 6 — pre-shell journey + Recharts tokens — 2026-07-06

Final "Study Desk" surface: extends the identity to the pre-shell journey and moves the
Progress chart colours to tokens. Spec: `docs/superpowers/specs/2026-07-06-redesign-journey-recharts.md`.

## What changed (files — presentation only)
- **Display headings** (`--font-display`, Lexend) on the journey's prominent headings:
  `welcome/Welcome.tsx` (title), `results/Results.tsx` (band-number h1),
  `onboarding/Onboarding.tsx` (3 step h2s), `placement/Generating.tsx`,
  `program/Program.tsx`, `milestones/Milestones.tsx` (h1s). Sizes/weights unchanged.
- **Welcome brand mark**: retired the `linear-gradient(135deg,…)` icon for the solid
  **ink mark** (`bg-[var(--color-text)]` + surface glyph) — matches the Sidebar.
- **Recharts tokens**: added `--color-skill-writing/speaking/reading/listening` in
  `app.css @theme`; `progress/Progress.tsx` now sources the 4 `<Line stroke>` from them
  (listening softened `#7c3aed → #6D5AE6`, a calmer indigo-violet).
- Placement: `PlacementRunner.tsx` has no prominent heading → no change (inherits tokens).

## Why
The journey headings still rendered in the body font and Welcome kept the old gradient
mark, so a new user met the pre-redesign look before the dashboard. The chart's line
colours were hardcoded hexes. This closes both.

## How to test / verify
- `cd web && npx tsc --noEmit && npm test` → clean, 66 passed (journey tests select by
  role/text, unaffected).
- Verified live in the owner's Chrome (after `docker compose up --build web` — the dev
  web image bakes source at build time): Welcome now shows the ink mark + Lexend title;
  Onboarding step heading in Lexend; warm canvas throughout.

## Caveats
- **Dev container caveat (reconfirmed):** the `web` service copies source at build time
  with no volume mount — after any frontend edit you must `docker compose up --build web`
  to see it (HMR only watches the baked snapshot). Documented in README.
- Login/Register/Passcode auth screens still carry the gradient icon (out of scope;
  small follow-up if wanted).

## Commit
- `29f63f3` — feat(ui): extend "Study Desk" identity to the journey + tokenize chart colours.

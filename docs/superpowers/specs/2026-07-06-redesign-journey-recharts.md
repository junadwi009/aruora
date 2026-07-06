# Redesign Design: pre-shell journey + Recharts tokens (Batch 6)

**Status:** proposed → awaiting approval · **Date:** 2026-07-06 · **Epic:** Phase 4 "Study Desk" rollout (final surfaces)

## Direction
Extend the already-approved "Study Desk" identity to the **pre-shell journey**
(Welcome → Onboarding → Placement → Generating → Results → Program → Milestones) so
a new user meets the same warm, editorial identity before reaching the dashboard.
Plus a small polish: move the Progress chart's hardcoded line colours to tokens.
Constraints unchanged: React 19 + Tailwind v4, **no new deps**, i18n, WCAG AA, a11y
fonts + dark mode + reduced-motion preserved, **function unchanged**, small diffs.

## Findings / scope
- **Display headings.** The journey's prominent `<h1>`/`<h2>` (Welcome `text-4xl`,
  Results band number `text-4xl`, Generating/Program/Milestones `text-2xl`,
  Onboarding step `text-lg`) render in the body font — they should use
  `--font-display` (Lexend) like the shell/Home, so the display face carries through.
- **Gradient brand mark (Welcome).** `welcome/Welcome.tsx` still uses the
  `linear-gradient(135deg, primary-600, primary-800)` icon (the "AI gradient"
  fingerprint retired in the Sidebar) → swap to the solid **ink mark**
  (`bg-[var(--color-text)]` + surface-coloured glyph) for consistency.
- **Placement.** `PlacementRunner.tsx` has no prominent heading (renders quiz items);
  it already inherits the warm tokens — no change.
- **Recharts colours (Progress).** `progress/Progress.tsx` hardcodes `#0d9488`
  (speaking), `#d97706` (reading), `#7c3aed` (listening); writing already uses a var.
  Introduce 4 `--color-skill-*` tokens in `app.css` and reference them, so the chart
  is themeable and consistent (incl. a dark-mode tune if needed).

## Non-goals
- No layout restructure of any journey screen (their layouts are already good) — this
  is a typographic + one-icon + token pass only.
- Login/Register/Passcode auth screens are not in scope (they share the gradient icon
  too; a small follow-up if wanted).
- No i18n/route/logic change.

## Testing
- `cd web && npx tsc --noEmit && npm test` → green (existing `program.test.tsx`,
  `onboarding.test.tsx`, `results.test.tsx`, `placement.test.tsx` must stay green;
  they select by role/text which is unaffected).
- Visual (owner's Chrome): step through the journey — headings now in Lexend, Welcome
  ink mark; Progress chart lines unchanged in hue but sourced from tokens; dark mode +
  a11y font still override headings.

## Boundary / risk
- Pure presentation: `style`/`className` on headings, one icon block, and a token
  block + 4 stroke references. Each file independently revertible. Recharts already
  resolves `stroke="var(--…)"` in this stack (grid/axes/writing line already do).

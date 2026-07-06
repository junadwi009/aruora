# Plan — pre-shell journey + Recharts tokens (Batch 6)

Spec: `docs/superpowers/specs/2026-07-06-redesign-journey-recharts.md`
Gate after each task: `cd web && npx tsc --noEmit && npm test`. Visual check in owner's Chrome at the end.

## Constraints
- No new deps, no layout restructure, no i18n/route/logic change. Keep journey tests green.

## Task 1 — Journey display headings
**Files:** `welcome/Welcome.tsx`, `onboarding/Onboarding.tsx`, `placement/Generating.tsx`,
`results/Results.tsx`, `program/Program.tsx`, `milestones/Milestones.tsx`
- [ ] Add `style={{ fontFamily: "var(--font-display)" }}` to each screen's prominent
  `<h1>`/`<h2>` (Welcome title; Results band number + section title; Generating,
  Program, Milestones h1; Onboarding step h2s). Keep existing size/weight/tracking.
- [ ] tsc + tests green.

## Task 2 — Welcome ink brand mark
**File:** `welcome/Welcome.tsx`
- [ ] Replace the gradient icon block with the solid ink mark
  (`bg-[var(--color-text)]`, glyph `text-[var(--color-surface)]`, `shadow-e2`) to match Sidebar.
- [ ] tsc + tests green.

## Task 3 — Recharts colour tokens
**Files:** `web/src/app.css`, `progress/Progress.tsx`
- [ ] `app.css`: add `--color-skill-writing/speaking/reading/listening` in `@theme`
  (writing = primary-600; speaking `#0D9488`; reading `#D97706`; listening `#6D5AE6`
  — a calmer indigo-violet than the raw `#7c3aed`); optional `.dark` tune for legibility.
- [ ] `Progress.tsx`: replace the 4 `<Line stroke=…>` values with `var(--color-skill-*)`.
- [ ] Verify the chart still renders with the tokened strokes (Chrome).

## Task 4 — Verify + wrap up
- [ ] Full gates: `npx tsc --noEmit && npm test` green.
- [ ] Visual: journey headings in Lexend, Welcome ink mark, chart lines from tokens; dark + a11y font still override.
- [ ] Write `logs/redesign-journey-recharts_2026-07-06_log.md`; commit; push; watch CI.

## Risk / rollback
- Presentation-only; each heading/icon/token edit is independently revertible. Journey
  tests select by role/text (unaffected). Lowest-risk batch of the redesign.

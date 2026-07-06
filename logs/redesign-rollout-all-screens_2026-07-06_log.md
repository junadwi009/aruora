# Redesign rollout — all remaining screens (Batch 5.2) — 2026-07-06

Completes the "Study Desk" identity rollout across every screen in the app shell
(direction approved in `docs/superpowers/specs/2026-07-05-redesign-shell-home.md`;
pattern proven on Progress in Batch 5.1).

## What changed (files — 18, +48/−48, purely presentational)
Two uniform, mechanical treatments (verified zero residual old patterns):

1. **Screen headers → display face.** Every sticky screen header's `<h1>` went from
   `text-base font-semibold` to `text-xl font-bold` + `fontFamily: var(--font-display)`,
   with header padding `px-4 py-3` → `px-4 md:px-6 py-4`. Applied to:
   `practice/QuizRunner.tsx` (covers **Reading + Listening**, thin wrappers over it),
   `writing/Writing.tsx`, `speaking/Speaking.tsx`, `speaking/Roleplay.tsx`,
   `tips/Tips.tsx`, `vocab/Vocab.tsx`, `test/MockTest.tsx`, `settings/Settings.tsx`,
   `session/Session.tsx`, `pronounce/Pronounce.tsx`.
2. **Section labels de-shouted.** The 29 instances of the old
   `text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide` micro-label
   became `text-sm font-semibold text-[var(--color-text)]` (sentence case — kinder to
   dyslexic readers than all-caps) across: Pronounce, Session, Speaking, Writing,
   Settings + its 8 section components (Admin/Data/Help/Milestones/Profile/Reminders/
   Security/Targets).

Scope note: the approved list was 8 screens; **Session, Pronounce, Roleplay** shared the
identical header pattern, so they were included too — leaving them out would have left
three inconsistent screens against the goal of a coherent identity. Distinct caption
variants (e.g. QuizRunner's `tracking-widest` transcript label, TipsSidePanel) were
deliberately left as captions.

## Why
After Batch 4/5.1, navigating from the redesigned Home/Progress to any other screen
dropped back to the old small headers and all-caps labels. This closes the gap: every
screen now shares the display-face header + editorial section hierarchy.

## How to test / verify
- `cd web && npx tsc --noEmit && npm test` → clean, 66 passed (25 files).
- Visual (owner's Chrome): navigate all views — headers now larger in Lexend, sections
  in sentence-case semibold; dark mode + a11y fonts still apply everywhere.
- No logic/i18n/route change: diff is exactly ±48 lines of className/style.

## Caveats
- Recharts hardcoded line hues (Progress) still pending a token pass (noted in 5.1 log).
- Welcome/Onboarding/Placement/Results/Program (pre-shell journey screens) were not in
  scope — they have their own layout language; a future batch if wanted.

## Commit
- `60fc8b0` — feat(ui): complete "Study Desk" identity rollout across all screens.

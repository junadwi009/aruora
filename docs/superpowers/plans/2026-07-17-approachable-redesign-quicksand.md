# Plan — "Approachable Premium" Redesign

Spec: `../specs/2026-07-17-approachable-redesign-quicksand.md`

## Phase 0 — Foundation (do first, verify before touching screens)
Because every heading uses `var(--font-display)` and every surface uses the token set,
this phase transforms all screens at once.
1. `web/src/fonts.css` — add `@fontsource/quicksand` weights 400/500/600/700.
   Install dep: `npm i @fontsource/quicksand` (in `web/`).
2. `web/src/app.css` —
   - `--font-display: "Quicksand", "Lexend", system-ui, sans-serif`.
   - primary `#6366F1` / 700 `#4F46E5`; warm bg `#FCFAF6`; dark bg `#12100E`.
   - add `--radius-2xl: 24px`, `--radius-3xl: 32px`; keep sm/md/lg.
   - add `--shadow-premium`, `--shadow-premium-card`; add `.premium-hover` utility + blob helper.
3. `components/ui/*` — Card default radius → `2xl`; add pill option to Button (primary CTA look);
   Badge/LevelChip → rounded-full soft indigo.
**Checkpoint:** run dev server, screenshot welcome + home in light & dark. Confirm typography+colour shift.

## Phase 1 — Entry / auth journey
`Welcome.tsx`, `AuthScreens.tsx`, `ResetPassword.tsx`, `PasscodeGate.tsx`.
Hero with gradient blobs + floating stat cards; auth cards centered with blob background,
pill CTA, uppercase field labels. **No pricing section** (skip prototype's welcome pricing grid).

## Phase 2 — Onboarding → placement → results
`Onboarding.tsx` (step bars + radio cards), `placement/*` (sticky header/footer, timer chip,
reading/listening/writing/speaking bodies), `Generating.tsx` (animated checklist + bar),
`Results.tsx` (radar + skill-bar cards).

## Phase 3 — Program / milestones
`Program.tsx` (pacing radio list), `Milestones.tsx` (timeline).

## Phase 4 — App shell + feature views
`AppShell.tsx` + `Sidebar.tsx` (rounded nav, help widget), `Home.tsx` (organic banner,
skill-track cards, profile/calendar/consistency widgets), then `reading/listening/speaking/
writing/pronounce/vocab/test/tips/progress/settings` view headers + card bodies.

## Phase 5 — Verify + finish
- `tsc --noEmit`, `npm run build`, `npm test` (web), API pytest unaffected.
- Visual pass light+dark for each screen in the user's browser.
- Secret scan, write update-log with commit hash.

## Execution notes
- Independent feature-view files → safe to parallelise across subagents once Phase 0 lands.
- Keep all copy in i18n; where prototype adds ID microcopy not yet keyed, add EN+ID keys.
- Do not alter journey/state/api/scoping logic — visual layer only.

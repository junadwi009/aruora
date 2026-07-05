# Plan — "Study Desk" redesign: shell + Home (Batch 4)

Spec: `docs/superpowers/specs/2026-07-05-redesign-shell-home.md`
Gates after each task: `cd web && npx tsc --noEmit && npm test`. Verify visually in the
owner's Chrome preview at the end of each visible task.

## Constraints
- No new dependency (reuse `@fontsource/lexend`, add its 700 weight import only).
- Keep `shell.test.tsx` green (roles, `aria-current`, level chip). All text via i18n.
- Preserve a11y fonts, dark mode, `prefers-reduced-motion`, AA.

## Task 1 — Design tokens (app.css) + display font
**Files:** `web/src/app.css`, `web/src/fonts.css`
- [ ] `fonts.css`: add `@import "@fontsource/lexend/700.css";`.
- [ ] `app.css`: add `--font-display` (Lexend stack); warm light neutrals (bg/surface/
  surface-2/border); warm dark neutrals a touch; keep accent + text/muted.
- [ ] Ensure the a11y-font setting overrides `--font-display` too (check `settings.ts`
  applies the chosen family to headings — wire `--font-display` to inherit when set).
- [ ] Re-verify muted (`#5B6675`) ≥4.5:1 on the new `--color-surface-2`; record ratio.
- [ ] Optional: subtle grain overlay utility (canvas only, pointer-events-none).

## Task 2 — Shell chrome (Sidebar, BottomTabs, AppShell)
**Files:** `components/menu/Sidebar.tsx`, `BottomTabs.tsx`, `AppShell.tsx`
- [ ] Sidebar: solid ink brand mark + Lexend wordmark (drop gradient); active item gets an
  accent bar + weight (not only bg tint); keep all `aria-current`, roles, level chips.
- [ ] BottomTabs: refine active indicator to match; keep roles/labels.
- [ ] AppShell: apply warm canvas; no structural/logic change (view registry untouched).
- [ ] tsc + tests green; preview check (desktop sidebar, mobile tabs, dark).

## Task 3 — Home hero + greeting + stat row
**Files:** `components/menu/Home.tsx`, `web/src/lib/i18n.tsx`
- [ ] Time-aware greeting in `--font-display` + subtitle; new i18n keys (EN + ID):
  `home.greetingMorning/Afternoon/Evening`, `home.greetingSub`.
- [ ] Rework Today hero (calmer surface, bigger CTA); streak + exam as a 2-up stat row.
- [ ] tsc + tests green; preview check.

## Task 4 — Home skill map, milestones, quick links + states
**Files:** `components/menu/Home.tsx`, `web/src/lib/i18n.tsx`
- [ ] Elevate skill map hierarchy (keep Card button a11y from Batch 3).
- [ ] Milestones **empty state** ("start your plan" nudge) + **skeleton** while loading;
  refine quick links. New i18n keys as needed (EN + ID).
- [ ] tsc + tests green; preview check.

## Task 5 — Verify + wrap up
- [ ] Full gates: `npx tsc --noEmit && npm test`. Optional `npm run e2e` (needs stack).
- [ ] Browser screenshots: Home + shell, light/dark, desktop/mobile.
- [ ] Write `logs/redesign-shell-home_2026-07-05_log.md` (files, contrast, screenshots, caveats, commit).
- [ ] Present; STOP for review. No merge/deploy.

## Risk / rollback
- Neutral-warming is the only global change (all screens) — revert the token block to
  undo. Everything else is scoped to `menu/` + additive i18n keys; each task is an
  independent, revertible diff pinned by tsc + `shell.test.tsx`.

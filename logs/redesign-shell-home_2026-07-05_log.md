# Redesign Batch 4 — "Study Desk" identity (shell + Home) — 2026-07-05

Phase 4 visual redesign: bold-but-calm editorial identity, scoped to the app shell +
Home. Spec: `docs/superpowers/specs/2026-07-05-redesign-shell-home.md`.
Approved: bold identity · warm neutrals shifted globally (owner-approved).

## What changed (files)
- `web/src/fonts.css` — import `@fontsource/lexend/700` (display weight). **No new package.**
- `web/src/app.css` —
  - `--font-display` token (Lexend) for brand + headings.
  - **Warm-paper neutrals (global, all screens):** light `bg #FAF8F3`, surface `#FFFDFA`,
    surface-2 `#F3F0E9`, border `#E8E2D6`, warm ink text `#17140F`/`#45403A`, muted `#6B6456`.
    Dark mode warmed to charcoal (`#14110C`…, muted `#A69C8A`).
- `web/src/lib/settings.ts` — a11y-font selection now also overrides `--font-display`
  (dyslexic/hyperlegible users get their face on headings too).
- `web/src/components/menu/Sidebar.tsx` — solid **ink brand mark** + display wordmark
  (dropped the 135° gradient); active nav item gets an **accent bar + weight** (not just
  a tint). All roles / `aria-current` / level chips preserved.
- `web/src/components/menu/Home.tsx` — **personal time-aware greeting** in display type;
  Today hero reworked as the centerpiece; streak + exam as a **2-up stat row**; section
  headings promoted to display (sentence case, not tiny all-caps); milestones now show a
  **skeleton** while loading and an **empty-state nudge** when there's no plan.
- `web/src/lib/i18n.tsx` — new EN + ID keys: `home.greetMorning/Afternoon/Evening`,
  `home.greetSub`, `home.milestonesEmpty`.

## Contrast (WCAG AA re-verified on the warm palette)
- Light muted `#6B6456`: 5.15–5.77:1 across bg/surface/surface-2 — all ≥4.5.
- Dark muted `#A69C8A`: 5.82–6.94:1. Body text ≥15:1 both modes.

## Why
The shell + Home read as generic (Inter-only, indigo "AI gradient" mark, cool slate,
flat one-column stack, impersonal "Dashboard"). The warm paper + Lexend display + editorial
hierarchy + personal greeting give a distinct, calm-premium identity without new deps or
heavy motion — and set the language for a later rollout to other screens.

## How to test / verify
- `cd web && npx tsc --noEmit && npm test` → clean, 66 passed. `shell.test.tsx` green.
- **Visual (owner's Chrome, per workflow):** `docker compose up --build` → http://localhost:5173.
  Check: warm canvas, serif-ish Lexend headings, greeting, sidebar ink mark + accent-bar
  active state; toggle dark mode + an a11y font (headings should switch too); mobile tabs.

## Caveats / scope
- Warm-neutral shift is **global** (all screens) by approval — other screens now sit on the
  warm canvas but keep their existing layouts until a later rollout batch.
- `BottomTabs` intentionally left structurally unchanged (token warmth flows through);
  can be refined in the rollout batch.
- Motion kept minimal; skeleton uses `animate-pulse`, auto-disabled under
  `prefers-reduced-motion` by the existing global rule.

## Commit
- Pending (working tree).

# Redesign Design: "Study Desk" identity — shell + Home (Batch 4)

**Status:** proposed → awaiting approval · **Date:** 2026-07-05 · **Epic:** Phase 4 visual redesign (bold identity, scoped)

## Design direction (approved: bold identity · scope: shell + Home)
A warm, **editorial "study desk"** identity — calm and premium, the opposite of a
test form. Distinct from the current cool-slate/indigo generic look via **typography,
warmth, hierarchy, and whitespace**, not via heavy motion or effects.

- **Purpose:** reduce exam anxiety; feel like a composed coach.
- **Constraints (hard):** React 19 + Vite + Tailwind v4; **no new dependency** (reuse
  installed `@fontsource/lexend`); all text via i18n; WCAG AA; a11y fonts + dark mode +
  `prefers-reduced-motion` preserved; **function unchanged**; small reviewable diffs.

## The identity (concrete)
1. **Display typography (no new dep).** Add `--font-display` = **Lexend** (already
   installed; import its 700 weight). Use for the brand wordmark and page headings —
   large, tight-tracked, confident. Body/UI stays Inter. When an a11y font is chosen
   (OpenDyslexic/Atkinson), `--font-display` follows it too (accessibility wins).
2. **Warm the neutrals (global token nudge, low-risk — affects all screens for
   coherence).** Light: `--color-bg #F8FAFC → #FAF8F3` (warm paper), `--color-surface
   #FFFFFF → #FFFDFA`, `--color-surface-2 #F1F5F9 → #F3F0E9`, `--color-border` warmer.
   Text/muted unchanged (re-verify muted stays ≥4.5:1 on the new surface-2). Dark mode
   warmed a touch. One accent kept: indigo `--color-primary-600` (AA-tuned).
3. **Signature details.** Retire the gradient brand mark for a solid ink mark + serif-ish
   Lexend wordmark; tinted (not pure-black) shadows already in place; a very subtle
   grain overlay on the app canvas (`pointer-events-none`, opacity ~2%).

## Scope of changes
- **AppShell / Sidebar / BottomTabs:** warm chrome, refined active state (accent bar +
  weight, not just tint), solid brand mark, section grouping label, current-view clarity.
- **Home:** 
  - **Personal, time-aware greeting** in display type ("Good evening, {name}" / localized)
    + one honest subtitle. New i18n keys (EN + ID) for greeting parts.
  - **Today hero** as the centerpiece: larger, calmer surface (drop the heavy left-border
    cliché), clear "start today's session" CTA.
  - **Stat row:** streak + exam countdown as a compact 2-up row (not two stacked cards).
  - **Skill map:** keep 2×2 (already keyboard-accessible via Batch 3), elevate hierarchy.
  - **Milestones + quick links:** refined; add an **empty state** when no plan/milestones
    ("start your plan" nudge) and **skeleton** placeholders while data loads.

## Non-goals
- No other screens (Reading/Writing/etc.) this batch — rollout later, batch by batch.
- No new libraries, no palette explosion (one accent), no heavy/parallax motion.

## Testing
- `cd web && npx tsc --noEmit && npm test` green (existing `shell.test.tsx` must pass —
  keep roles/labels/`aria-current`).
- Re-verify muted contrast ≥4.5:1 on the new warm `--color-surface-2` (document ratio).
- **Browser preview** (owner's Chrome) for the visual pass — screenshots of Home +
  shell, light & dark, desktop & mobile.

## Boundary / risk
- The neutral-warming touches global tokens (all screens) for coherence — the one change
  beyond shell+Home; low-risk (contrast preserved), flagged for approval.
- Everything else is scoped to `menu/` + a few new i18n keys. Reversible per file.

# Spec — "Approachable Premium" Redesign (Quicksand + warm-paper refresh)

**Date:** 2026-07-17
**Source of truth:** `ielts_coach_approachable_redesign_with_idr_pricing.html` (static prototype, ID copy)
**Owner decision (this session):** full screen-by-screen rebuild · adopt Quicksand headings · **skip** IDR pricing / promo modal.

## Goal
Apply the prototype's warm, rounded, "approachable premium" visual language across the
whole React app **without** regressing behaviour, i18n, a11y, or multi-user scoping.

## What changes (design language)
1. **Type** — Quicksand becomes the display/heading face (`--font-display`). Body stays
   Inter (`--font-ui`), reading passages stay Lexend (`--font-reading`). A11y font override
   (`settings.ts`) already retargets `--font-display`, so dyslexic/hyperlegible users are unaffected.
2. **Colour** — warm-paper palette nudged to the prototype: primary indigo `#6366F1`
   (hover `#4F46E5`), warm bg `#FCFAF6`, dark bg `#12100E`. CEFR/skill/semantic tokens kept.
3. **Shape** — larger radii: cards `24px`, big surfaces `32px`; primary CTAs become **pills**
   (`rounded-full`). Add `--radius-2xl: 24px`, `--radius-3xl: 32px`.
4. **Elevation** — indigo-tinted "premium" shadows + a `premium-hover` lift utility.
5. **Motif** — soft blurred gradient blobs behind auth/onboarding/generating/milestones;
   pill CTAs with trailing arrow; uppercase micro-labels; rounded chips.

## What does NOT change
- Routing/journey state machine (`lib/journey.tsx`), API client, data scoping, auth.
- The `--font-reading` Lexend passages (readability engine) and a11y font override.
- No new runtime CDN (Quicksand self-hosted via `@fontsource/quicksand`).
- No pricing screen, no promo modal, no billing toggle (explicitly out of scope).

## Screen inventory (prototype → real component)
| Prototype state | Real component |
|---|---|
| welcome (+ hero, floating stat cards) | `welcome/Welcome.tsx` |
| login / forgot / register | `auth/AuthScreens.tsx`, `auth/ResetPassword.tsx` |
| onboarding (3 steps) | `onboarding/Onboarding.tsx` |
| intro / placement (4 sections) | `placement/*` |
| generating | `placement/Generating.tsx` |
| results (radar + skill bars) | `results/Results.tsx` |
| program (pacing) | `program/Program.tsx` |
| milestones | `milestones/Milestones.tsx` |
| app shell + sidebar | `menu/AppShell.tsx`, `menu/Sidebar.tsx` |
| home dashboard | `menu/Home.tsx` |
| reading/listening/speaking/writing/pronounce/vocab/test/tips/progress/settings | matching folders |

## Constraints / acceptance
- All UI strings via i18n (EN+ID) — no hardcoded copy added.
- Light + dark both correct; reduced-motion respected.
- `npm run build` + `tsc --noEmit` clean; existing Vitest/Playwright still pass.
- Verify visually in the user's browser (dev server) before claiming done.
- Update-log written to `logs/` per hard rule #1.

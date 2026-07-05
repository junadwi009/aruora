# Accessibility Design: contrast + dialog focus + radio semantics (Batch 2)

**Status:** proposed → awaiting approval · **Date:** 2026-07-05 · **Epic:** Post-audit a11y remediation (findings H2, H3, M3)

## Design direction (Phase 4 gate)
- **Purpose:** a calm, focused IELTS study tool. Legibility over flourish.
- **Audience:** learners, including dyslexic readers (OpenDyslexic / Atkinson fonts).
- **Principle for this batch:** *correctness, not restyle.* Keep the current visual
  language, spacing, and components. Only raise contrast to WCAG AA, make the modal
  and radio groups fully keyboard/SR-accessible. **Preserve** the a11y fonts, the
  `prefers-reduced-motion` block, dark mode, and the existing focus-visible rings.
- **Constraints:** stay in React 19 + Tailwind v4; **no new dependency** (hand-roll
  the focus trap); all text via i18n; no schema/API change.

## Findings addressed
- **H2** — token `--color-muted #64748B` fails WCAG AA for small text (~4.4:1 on white, ~3.9:1 on `--color-surface-2`). Used for placeholders, helper text, inactive nav, disabled, secondary labels. ([app.css:26](../../../web/src/app.css))
- **H3** — `Dialog` has no focus trap, no focus restore on close, and `aria-modal` on the wrong node. ([Dialog.tsx](../../../web/src/components/ui/Dialog.tsx))
- **M3** — `RadioCard` supports Enter/Space but no Arrow-key navigation, and its groups lack a `role="radiogroup"` wrapper. ([RadioCard.tsx](../../../web/src/components/ui/RadioCard.tsx), used in Onboarding + Program)

## Design
- **H2 (one-token fix).** Darken **light-mode** `--color-muted` from `#64748B` to an
  AA-safe slate (target ≥4.5:1 on `--color-surface-2 #F1F5F9`; candidate `#5B6675`,
  verified after applying). Dark-mode `--color-muted #94A3B8` already clears AA on
  the lightest dark surface (~5.1:1) → unchanged. Single change fixes every usage.
- **H3 (Dialog).** In `Dialog.tsx`: on open, store `document.activeElement`, move
  focus into the panel; on close/unmount, restore focus to the stored element. Trap
  Tab/Shift+Tab within the panel's focusable set (wrap at both ends). Move
  `aria-modal="true"` onto the `role="dialog"` panel; drop it from the outer
  container. Escape-to-close and the close button are retained.
- **M3 (RadioCard).** Add roving Arrow-key handling: Down/Right → focus next
  `[role="radio"]` within the closest `[role="radiogroup"]`; Up/Left → previous
  (wrap-around). Keep `role="radio"`, `aria-checked`, and the title as the
  accessible name. Wrap the groups in `Onboarding.tsx` and `Program.tsx` in
  `<div role="radiogroup" aria-label={t(...)}>`. New i18n keys for the group labels.

## Non-goals
- No visual redesign, no spacing/typography overhaul, no color palette expansion
  beyond the single muted token. (A broader visual pass, if wanted, is a later batch
  with its own design declaration.)
- M4 (Card `interactive` div-as-button) is deferred to a follow-up mini-batch.

## Testing
- **Contrast (H2):** after the token change, assert the computed value in a small
  unit/DOM check or document the measured ratio in the log (≥4.5:1 on surface-2).
- **Dialog (H3):** vitest — renders with `role="dialog"` + `aria-modal="true"` on the
  panel; Escape calls `onClose`; focus lands inside on open. (Full Tab-cycle is
  asserted as far as jsdom allows.)
- **RadioCard (M3):** vitest — ArrowDown moves focus to the next radio; group has
  `role="radiogroup"`. Existing `program.test.tsx` (selects "90-day plan" by role)
  must stay green.
- Gates: `cd web && npm test && npx tsc --noEmit`.

## Boundary
Batch 2 = `app.css` (1 token) + `Dialog.tsx` + `RadioCard.tsx` + 2 group wrappers +
i18n keys + tests. No backend. No new deps.

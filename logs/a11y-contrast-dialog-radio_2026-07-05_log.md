# A11y Batch 2 — contrast + dialog focus + radio keys — 2026-07-05

Closes audit findings **H2, H3, M3** (see `docs/superpowers/specs/2026-07-05-a11y-contrast-dialog-radio.md`).
Correctness pass only — no visual redesign. TDD (vitest) for the behavioural fixes.

## What changed (files)
- `web/src/app.css` — **H2**: light-mode `--color-muted` `#64748B` → `#5B6675`.
  Measured contrast (WCAG): **5.3:1 on `--color-surface-2` (#F1F5F9)** and **5.8:1 on
  white** (was 3.9:1 / 4.4:1 — failing AA). Dark-mode `--color-muted #94A3B8` left
  unchanged (already ~5.1:1 on the lightest dark surface). One-token fix → covers
  every muted usage (placeholders, helper text, inactive nav, disabled, labels).
- `web/src/components/ui/Dialog.tsx` — **H3**: saves the previously-focused element
  and restores it on close; moves focus into the panel on open; traps Tab/Shift+Tab
  within the panel (wraps at both ends); `aria-modal="true"` moved onto the
  `role="dialog"` panel (was on the outer container). Escape-to-close retained.
- `web/src/components/ui/RadioCard.tsx` — **M3**: added roving Arrow-key navigation
  (Down/Right → next, Up/Left → previous, wrap-around) scoped to the enclosing
  `role="radiogroup"`. Enter/Space select unchanged.
- Tests (new): `web/src/components/ui/dialog.test.tsx` (4), `radiocard.test.tsx` (4).

**Corrections (verified during impl):** the audit's "missing `role=radiogroup`
wrapper" was a false positive — both consumers already wrap their groups
(`Onboarding.tsx:105` `aria-label={t("onb.goal")}`, `Program.tsx:72`
`aria-label={t("program.durationAria")}`). So M3 was only the arrow-key gap; no
consumer or i18n change was needed.

## Why
`--color-muted` (the shared secondary-text token) failed WCAG AA for small text; the
modal was not keyboard/SR-safe (no trap, no focus restore, `aria-modal` on the wrong
node); radio groups lacked arrow-key navigation expected of the radio pattern.

## How to test / verify
- `cd web && npx tsc --noEmit` → clean.
- `cd web && npm test` → 63 passed (incl. the 8 new a11y tests).
- Browser (owner's active Chrome preferred, per workflow): open onboarding/program
  (radio arrow-keys) and the Progress history modal (Tab stays trapped, focus
  returns to the trigger on close); check secondary text legibility.

## Caveats / known limits
- Focus-trap uses a standard focusable-selector query; deeply custom widgets inside a
  dialog with their own focus management are out of scope (none exist today).
- Contrast verified by computation + documented ratios; a full axe-core sweep is a
  possible follow-up.
- Preserved intentionally: a11y fonts, `prefers-reduced-motion`, dark mode,
  focus-visible rings. M4 (Card `interactive` div-button) deferred to a mini-batch.

## Commit
- `f5ed993` — fix(a11y): AA contrast, dialog focus trap, radio arrow-keys. Not pushed.

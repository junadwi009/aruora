# Plan — a11y contrast + dialog focus + radio semantics (Batch 2)

Spec: `docs/superpowers/specs/2026-07-05-a11y-contrast-dialog-radio.md`
Gates after each task: `cd web && npx tsc --noEmit && npm test`.

## Constraints
- No new dependency; hand-roll the focus trap. All UI text via i18n. No backend change.
- Preserve a11y fonts, `prefers-reduced-motion`, dark mode, focus-visible rings.

## Task 1 — H2: darken the muted token
**File:** `web/src/app.css`
- [ ] Change light `--color-muted: #64748B` → `#5B6675` (or nearest AA-safe slate).
- [ ] Verify contrast ≥ 4.5:1 on `#F1F5F9` and `#FFFFFF`; record the ratio in the log.
- [ ] Leave dark-mode `--color-muted` unchanged (already AA).

## Task 2 — H3: Dialog focus trap + restore + aria-modal
**Files:** `web/src/components/ui/Dialog.tsx`, `web/src/components/ui/dialog.test.tsx` (new)
- [ ] Store `document.activeElement` on open; restore it on close/unmount.
- [ ] On open, move focus to the first focusable element in the panel (fallback: panel).
- [ ] Add `onKeyDown` Tab trap over the panel's focusable set (wrap both ends).
- [ ] Move `aria-modal="true"` to the `role="dialog"` panel; remove from the container.
- [ ] Test: role="dialog" + aria-modal on panel; Escape → onClose; focus inside on open.

## Task 3 — M3: RadioCard arrow-keys
**Files:** `web/src/components/ui/RadioCard.tsx`, `components/ui/radiocard.test.tsx` (new)
- [x] RadioCard `onKeyDown`: Arrow Down/Right → focus next `[role="radio"]` in closest `[role="radiogroup"]`; Up/Left → previous (wrap). Keep Enter/Space select, `role="radio"`, `aria-checked`, title as name.
- [ ] Test: ArrowDown moves focus to next radio; ArrowUp wraps; Enter selects.
- **CORRECTION (verified):** the `role="radiogroup"` wrappers **already exist** —
  Onboarding.tsx:105 (`aria-label={t("onb.goal")}`) and Program.tsx:72
  (`aria-label={t("program.durationAria")}`). The audit's "missing wrapper" was a
  false positive. No consumer/i18n change needed; only the arrow-key gap was real.

## Task 4 — Green + regression
- [ ] `cd web && npx tsc --noEmit` → clean.
- [ ] `npm test` → all green, incl. existing `program.test.tsx` / `onboarding.test.tsx`.
- [ ] (If e2e relevant) note `npm run e2e` for manual run — needs the compose stack.

## Task 5 — Wrap up
- [ ] Write `logs/a11y-contrast-dialog-radio_2026-07-05_log.md` (files, measured contrast, how to test, caveats, commit hash).
- [ ] Present diff summary; STOP for review.

## Risk / rollback
- H2 is a 1-line token change (revert trivially). H3/M3 are additive a11y behavior;
  existing role/name-based tests are preserved. Focus-trap edge cases are the main
  risk — covered by the new Dialog test and manual keyboard check.

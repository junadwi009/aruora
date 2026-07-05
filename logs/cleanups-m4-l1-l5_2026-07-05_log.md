# Cleanups Batch 3 — M4 + L1–L5 — 2026-07-05

Final audit batch: one interactive-a11y fix (M4) + low-severity i18n / dead-code /
quality / auth tidy-ups. Spec: `docs/superpowers/specs/2026-07-05-cleanups-m4-l1-l5.md`.

## What changed (files)
- **M4** `web/src/components/ui/Card.tsx` — when `variant="interactive"` and an
  `onClick` is present, the card now renders `role="button"`, `tabIndex={0}`, a
  `focus-visible` ring, and Enter/Space activation. Fixes every interactive card
  (e.g. Home skill map) in one place. Non-interactive cards unchanged.
- **L1** `web/src/components/menu/Home.tsx` — milestone "Day N" now uses
  `t("session.day")` (EN "Day" / ID "Hari") instead of a hardcoded "Day ".
- **L2** `web/src/components/settings/Settings.tsx` — language button "Indonesia" →
  "Bahasa Indonesia" (endonym, clearer).
- **L3** `web/src/components/menu/Sidebar.tsx`, `Home.tsx` — removed the unused
  `label` field (+ type) from NAV_ENTRIES and SKILLS (UI renders via `t("nav."+…)`).
- **L4** `api/app/services/llm.py` — `except (KeyError, Exception)` → `except Exception`.
- **L5** `api/app/routes/account.py` — `google_login` only adopts the Google email
  when `email_verified` is truthy (sign-in by `google_sub` still works).

## Tests
- `web/src/components/ui/card.test.tsx` (new, 3): interactive Card is a keyboard
  button (Enter + Space); plain card is not a button.
- `api/tests/test_google_auth.py` — canonical CLAIMS now include `email_verified:True`;
  added `test_google_unverified_email_not_adopted` (unverified email is not adopted).

## Why
Close the remaining audit findings: keyboard access for clickable cards, full i18n
coverage, dead-code removal, a tidy exception, and anti-takeover on Google sign-in.

## How to test / verify
- `cd web && npx tsc --noEmit && npm test` → clean, 66 passed.
- `cd api && .venv/Scripts/python -m pytest -q` → all green.

## Caveats / accepted risk
- **Register enumeration** (L5b) intentionally left as-is: the "already registered"
  message is a UX affordance and the endpoint is rate-limited (5/min). Documented,
  not changed.
- L2 keeps endonyms untranslated by design (users find their own language).

## Commit
- `9a1ba2c` — fix: audit cleanups batch 3 (M4 + L1-L5). Not pushed.

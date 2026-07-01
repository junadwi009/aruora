# tips-reference-rail — 2026-07-01

Owner noticed the Tips page left the right half of wide screens empty and
suggested filling it with target scores / per-level criteria.

## What changed (`8348448`)
- New `web/src/components/tips/TipsSidePanel.tsx` — a right-hand aside:
  1. **Level & target kamu** — per skill: current CEFR chip (or "Belum dinilai")
     and, when set, the target chip; plus the overall target band. Falls back to
     "Atur target di Pengaturan" when there's nothing yet. Data from
     `api.skillLevels()` + `api.accountMe()`; both failures are swallowed so the
     panel still renders.
  2. **Acuan Band → CEFR** — static reference: 8.0+→C2, 7.0–7.5→C1, 6.0–6.5→B2,
     4.5–5.5→B1, ≤4.0→A1/A2 (same thresholds the examiner prompts use), each with
     a one-line Indonesian description + an "approximate mapping" hint.
- `Tips.tsx` — the content area is now `flex-col xl:flex-row`: the accordion list
  keeps its `max-w-2xl` on the left, the panel sits on the right and is `xl:sticky`.
  On < xl screens it stacks below the tips (no layout regression on mobile).
- `lib/i18n.tsx` — added the panel's EN + ID keys.
- `tips.test.tsx` — extended the `api` mock with `skillLevels` + `accountMe` (the
  panel calls them on mount).

## Verify
- `tsc --noEmit` clean; `vitest run` → **55 passed**.
- Live (docker compose up --build web): signed in, Tips page now shows both cards
  filling the right column — "Level & target kamu" (Target band 6.0, skills
  "Belum dinilai" for an un-placed account) and the colour-coded "Acuan Band →
  CEFR" table. All Indonesian.

## Notes
- The Band→CEFR mapping is intentionally labelled approximate — official IELTS
  uses full band descriptors, not a fixed band↔CEFR table.
- Per-skill targets show only when the user set them (Settings → Targets); current
  levels appear once placement/practice has assessed a skill.

## Commit
- `8348448` feat(tips): reference rail — level/target + Band→CEFR on wide screens

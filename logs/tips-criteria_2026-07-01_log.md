# tips-criteria — 2026-07-01

Owner asked for more detailed, skill-specific criteria per level so a learner can
self-assess their progress — e.g. Reading = roughly what share of questions you
can answer, Speaking = how far you can explain / be understood.

## What changed (`1562d24`)
- `TipsSidePanel.tsx` — replaced the static Band→CEFR card with an **interactive
  per-skill criteria ladder**:
  - A 4-way skill toggle (Reading / Listening / Writing / Speaking).
  - Five levels (C2 → A1/A2) each with band range + a **concrete, self-assessable
    descriptor** for the selected skill:
    - Reading & Listening cite an approximate **share of questions** correct
      (e.g. B2 ≈ 55–70%).
    - Writing & Speaking describe **how far you can produce / be understood**
      (e.g. Speaking B1 "…masih ada jeda… Umumnya dipahami").
  - The learner's **current level for that skill is highlighted** ("kamu"), so
    they can locate themselves and read what the next level requires.
  - The "Level & target kamu" summary card is kept above it.
- `i18n.tsx` — 20 `crit.<skill>.<level>` descriptor keys + labels
  (`tips.criteria`, `tips.criteriaHint`, `tips.here`), EN + ID.

### Layout fix (important)
The first rail used `xl:flex-row` with a `w-full`/`max-w` left column. Two problems
surfaced in the browser:
1. the **xl breakpoint (1280px) never activated** at the owner's window width
   (~1254 CSS px behind a 1.25 DPR), so the rail silently fell back to a stacked
   layout; and
2. even when it did apply, 672 + 384 columns **overflowed** the ~968px main area,
   cutting the panel off on the right.
Fixed by switching to a `lg:grid lg:grid-cols-[1fr_18rem]` (activates at 1024px and
sizes to fit): verified in-browser `document.scrollWidth == innerWidth` (no
horizontal overflow), grid columns `905px + 288px`, panel fully visible.

## Verify
- `tsc --noEmit` clean; `vitest run` → **55 passed**.
- Live (docker compose up --build web): panel renders fully (no cut-off); toggling
  skills swaps descriptors (Reading shows question-share, Speaking shows
  understanding); all Indonesian. Confirmed layout via page JS (no overflow).

## Notes
- Question-share bands are deliberately approximate self-check guidance, not the
  official raw→band table.
- Current-level highlight appears once placement/practice has assessed that skill;
  an un-placed account shows all levels without a highlight.

## Commit
- `1562d24` feat(tips): per-skill self-assessment criteria + fix rail layout

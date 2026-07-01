# tips-3col-layout — 2026-07-01

Owner: the skill-toggle button labels were still truncated in the narrow rail;
suggested a 3-column container.

## What changed (`2cb09d3`)
- **Skill toggle → 2×2 grid** (`grid-cols-2`) instead of 4-across. The long
  Indonesian labels (Membaca / Menyimak / Menulis / Berbicara) no longer truncate.
- **3-column page on wide screens.** `TipsSidePanel` now returns the two cards as a
  fragment (not a wrapping `<aside>`), so they become direct grid items. Tips.tsx
  container:
  - mobile: single stacked column;
  - `lg` (≥1024): 2 columns `[1fr 19rem]` — tips list `lg:row-span-2`, the two cards
    stacked in the right column;
  - `xl` (≥1280): 3 columns `[1fr 19rem 19rem]` — tips | Level&Target | Criteria,
    each card in its own column (`xl:row-span-1` releases the span).

## Verify
- `tsc --noEmit` clean; `vitest run` → **55 passed**.
- Live (docker compose up --build web), in Chrome: grid computed
  `560.8px 304px 304px`; page JS check `anyTabCut=false` and
  `scrollWidth==innerWidth` (no horizontal overflow). All four toggle labels fully
  visible; criteria ladder reads cleanly.

## Commit
- `2cb09d3` fix(tips): 3-column layout + 2×2 skill toggle (no truncated buttons)

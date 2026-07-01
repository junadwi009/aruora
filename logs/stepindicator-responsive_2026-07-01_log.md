# stepindicator-responsive — 2026-07-01

Owner: on the onboarding card, step "3" (Target band Anda) spilled **outside** the
card. Make the UI responsive so it doesn't overflow.

## Cause
`StepIndicator` rendered each step label with `whitespace-nowrap` inside a plain
`flex` row with no width bound. The English labels fit `max-w-md`, but the longer
Indonesian labels ("Mengapa Anda mengambil IELTS?", …) forced the row wider than
the card → the last step overflowed the right edge.

## Fix (`d26dd45`)
Rewrote `web/src/components/ui/StepIndicator.tsx` to be responsive:
- Container `flex w-full items-start`.
- Each step is a **fixed-width `w-20` centred column** whose label **wraps**
  (`break-words`, `leading-tight`, `text-[11px]`) instead of `whitespace-nowrap`.
- Connectors are `flex-1 min-w-2` so they absorb the remaining width and shrink on
  narrow screens; aligned to the circle with `mt-4`.

Result: the indicator always fits its container regardless of label length or
language. (Shared component — also benefits any other screen using it.)

## Audit for other overflow risks
Grepped components for `whitespace-nowrap` / large fixed widths: the only
`whitespace-nowrap` was StepIndicator (fixed). The rest are `max-w-[…]` (which
constrain, safe) or small `min-w-[…rem]` on centred buttons — no other overflow.

## Verify
- `tsc` clean; `vitest run` (ui + onboarding) → 5 passed.
- Live (docker compose up --build web), Indonesian: onboarding step labels wrap
  under each circle; page JS measured the indicator's right edge (971) **inside**
  the card (992) — `overflowsCard:false`, `scrollWidth == innerWidth`. Confirmed in
  Chrome (all three steps within the card).

## Commit
- `d26dd45` fix(ui): responsive StepIndicator — labels wrap, no card overflow

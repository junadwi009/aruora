# Update log — "Approachable Premium" redesign (Quicksand + warm-paper)

**Date:** 2026-07-17
**Spec/plan:** `docs/superpowers/specs/2026-07-17-approachable-redesign-quicksand.md` ·
`docs/superpowers/plans/2026-07-17-approachable-redesign-quicksand.md`
**Commit:** `48dc7b6`

## What changed & why
Applied the `ielts_coach_approachable_redesign_with_idr_pricing.html` prototype's visual
language across the whole web app. Owner chose: full screen-by-screen rebuild · adopt
Quicksand headings · **skip** the prototype's IDR pricing / promo modal (app is a
local-first prep tool, not a paid product).

### Foundation (propagates app-wide)
- `web/package.json` — added `@fontsource/quicksand` (self-hosted, no CDN).
- `web/src/fonts.css` — import Quicksand 400/500/600/700.
- `web/src/app.css` —
  - `--font-display` → Quicksand stack (headings/brand; a11y-font override still wins).
  - Warm palette to match prototype: bg `#FCFAF6`, surface `#FFFFFF`, dark bg `#12100E`, etc.
  - New radii `--radius-2xl: 24px`, `--radius-3xl: 32px`.
  - New indigo-tinted `--shadow-premium{,-card,-hover}` (dark-mode variants too).
  - New helpers: `.premium-hover` (lift), `.premium-blob` (decorative gradient blob).
- `web/src/components/ui/Card.tsx` — default radius → 2xl; premium shadows; interactive = premium-hover.
- `web/src/components/ui/Button.tsx` — new `pill` prop (fully-rounded CTA); primary hover shadow → premium-card.

### Screens (visual-only rebuilds — logic/props/i18n/a11y preserved)
- **Welcome** — hero with gradient blobs, brand header, big Quicksand headline, pill CTAs,
  decorative panel with floating stat cards. No pricing section.
- **Auth** — `AuthForm`, `ForgotPassword`, `ResetPassword`, `PasscodeGate`: blob background,
  primary icon tile, rounded-3xl card, uppercase micro-labels, pill CTAs.
- **Onboarding / Generating / Results** — step bars, radio cards, animated checklist, radar + skill-bar cards.
- **Placement** — sticky header/footer chrome, timer/section pill chips, restyled bodies (Lexend passages kept).
- **Program / Milestones** — centered premium cards, pacing radio list, numbered timeline.
- **App shell** — `Sidebar` (primary brand tile, rounded nav, "Need guidance?" help widget),
  `BottomTabs` (active pill), `Home` (organic banner hero, richer skill cards, real streak/exam
  right-rail — no fabricated calendar/mentor widgets).
- **Feature views** — reading, listening, writing, speaking, roleplay, pronounce, quiz, vocab,
  test, tips, progress, session, settings: icon-tile headers + rounded-3xl premium cards.

### i18n
Added EN+ID keys only where new copy was introduced (all via the i18n system, hard rule #3):
`welcome.badge`, `welcome.stat*`, `welcome.footnote`, `menu.helpTitle`, `menu.helpSub`.

## How to test
- `docker compose up --build` (web :5173, api :5050) — or `cd web && npm run dev`.
- Walk the journey: welcome → auth → onboarding → placement → generating → results →
  program → milestones → app; toggle dark mode + each font in Settings.
- `cd web && npx tsc --noEmit && npm run build && npm test`.

## Caveats
- Prototype's pricing tiers / promo modal intentionally omitted.
- Prototype's decorative calendar / mentor / profile widgets on the dashboard were NOT
  copied — they showed fabricated data; the real Home keeps genuine streak/exam/milestone data.
- Band/CEFR figures shown remain ESTIMATES (unchanged copy).

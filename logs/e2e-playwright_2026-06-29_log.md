# e2e-playwright — 2026-06-29

Phase 2d-6: a Playwright end-to-end smoke against the running stack.

## What changed
- `web/package.json` — `@playwright/test` devDep + scripts `e2e` / `e2e:install`.
- `web/playwright.config.ts` — testDir `e2e`, baseURL `E2E_BASE_URL ?? http://localhost:5173`, chromium project.
- `web/e2e/journey.spec.ts` — 3 tests: (1) app loads, "IELTS Coach"/"Dashboard" visible, no `Uncaught`/`is not a function` console errors; (2) enter app shell (via the Welcome "I already have a profile" shortcut, resilient to whether a profile exists) → navigate to **Vocabulary**; (3) enter shell → open the **Mock Test**.
- `web/vite.config.ts` — vitest `include: ["src/**/*.{test,spec}.{ts,tsx}"]` so it ignores the Playwright `e2e/` specs.
- `.gitignore` — Playwright artefacts.

## How to run
- `docker compose up -d --build` (web must serve current source — see caveat).
- `cd web && npm run e2e:install` (one-time chromium download) then `npm run e2e`.

## Verify
- `npx playwright test` → **3 passed** against the live compose stack. `npm test` (vitest) → 35 still green (scoped to src/).

## Caveat found & fixed during verification
- The `web` container's Dockerfile **copies source at build time** (no bind-mount), so a running `web` from an earlier build serves **stale UI**. The e2e initially failed (Vocab/Mock absent) until `docker compose up -d --build web` rebuilt it. Lesson: always `--build web` after frontend changes before e2e / manual QA.

## Commits
- `44aebbf` test(e2e): Playwright journey smoke against the live stack

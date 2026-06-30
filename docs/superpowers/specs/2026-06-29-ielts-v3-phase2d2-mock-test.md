# Phase 2d-2 Design: Mock Test (Listening + Reading)

**Status:** approved (batch "lanjut semua berurutan") → implementation · **Date:** 2026-06-29

## Goal
Activate the **Test** tab: a timed Listening + Reading mock, graded locally, scored to approximate bands, persisted to the idle `mocks` table, and surfaced on Progress.

## Scope
In: `mocks` persistence (POST/GET), a two-section MockTest runner (Listening → Reading → result), band approximation, Progress mock section. Out: Writing/Speaking in the mock, full 4-skill exam, official raw→band tables (approximation only). `cards` stays idle.

## Backend (TDD)
- Repo: `save_mock(listening, reading, overall) -> int`; `list_mocks() -> list[dict]` (newest-first: id, listening, reading, overall, createdAt).
- Routes `mocks.py`: `POST /api/mocks {listening,reading,overall}` → `{id}`; `GET /api/mocks` → list. Register blueprint. (Matches v1 contract.)
- No schema change (`mocks` table exists: listening, reading, overall, created_at).

## Frontend (TDD)
- `lib/band.ts`: `bandFromPct(pct) -> number` piecewise approx (≥90→8, ≥80→7.5, ≥70→7, ≥60→6.5, ≥50→6, ≥40→5.5, ≥30→5, else 4.5). Pure, tested.
- `client.ts`: `mocksList()`, `mockSave({listening,reading,overall})` + `MockScore` type.
- `components/test/MockTest.tsx` (replaces the "coming soon" placeholder in viewRegistry `test`): intro → fetch a listening set + a reading set (`practiceSet`) → answer each section (compact inline question list, local grade) with a single overall countdown (e.g. 30 min) → result card (L band, R band, overall = round mean to .5) → auto-`mockSave` → CTA to Progress. Bands labelled estimates.
- `Progress.tsx`: also fetch `mocksList()`; render a "Mock tests" history section (date · L/R/overall) when present.

## Testing
api: repo save/list mock; routes POST→id + GET list. web: bandFromPct vectors; client URLs; MockTest smoke (renders intro → start). 

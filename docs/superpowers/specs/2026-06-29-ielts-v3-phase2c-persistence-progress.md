# IELTS Coach v3 — Phase 2c Design: Attempt Persistence + Progress Analytics

| | |
|---|---|
| **Status** | Approved (verbal) → implementation |
| **Date** | 2026-06-29 |
| **Phase** | 2c (follows 2a live-LLM, 2b-1 essay-metrics, 2b-2 ASR) |
| **Owner** | Arjuna D. Putranto |

## 1. Goal
Persist Writing & Speaking evaluations and surface them on the Progress tab as band trends + a clickable history that re-opens the exact past feedback. Unlocks the data chain the 30-day plan needs (per-skill trend visibility). The `attempts` table already exists and is currently idle.

## 2. Scope
**In:** persist Writing/Speaking attempts on evaluate; 3 read endpoints (history list, history detail, trends); Progress UI (trend chart + history list + feedback dialog).
**Out (→ Phase 2d):** Mock Test assembly (Listening+Reading, timed, `mocks` table) and Reading/Listening *practice* persistence — different data paths, separate phase. `lessons`/`cards` tables remain idle (later phases).

## 3. No schema change
Reuse existing `attempts` columns. Mapping:
- `type` = `writing` | `speaking`; `task` = taskType / part; `prompt` = prompt / question; `body` = essay / transcript; `cefr`.
- `bands` (JSON) = the full gateway bands dict — **includes `overall`** (writing: taskResponse/coherenceCohesion/lexicalResource/grammaticalRange/overall; speaking: fluencyCoherence/lexicalResource/grammaticalRange/pronunciation/overall). Source of trend lines.
- `criteria` (JSON) = the remaining feedback payload so detail re-renders identically — writing: `{corrections, rewrite}`; speaking: `{feedback, modelAnswer}` (+ `stub` flag).
- `metrics` (JSON) = essay metrics (writing) / `{}` (speaking).

## 4. Backend
- **Repository** (`repositories.py`): `save_attempt(type, task, prompt, body, bands, criteria, cefr, metrics)->int`; `list_attempts(type=None)->list[dict]` (id, type, task, cefr, overall, createdAt — newest first); `get_attempt(id)->dict|None` (full reconstructed eval payload + meta); `trends()->{writing:[...], speaking:[...]}` (each point: createdAt, overall, criteria bands).
- **Routes**: `writing/evaluate` & `speaking/evaluate` call `repo.save_attempt(...)` after scoring and add `savedId` to the response (additive — existing fields unchanged). New read blueprint `history.py`: `GET /api/history/attempts?type=`, `GET /api/history/attempt/<id>`, `GET /api/stats/trends`. NOT_FOUND(404) on missing id.
- **Contracts**: read endpoints return plain camelCase dicts (consistent with repo style). No key leak (evals already sanitised).

## 5. Frontend
- **client.ts**: `historyAttempts(type?)`, `historyAttempt(id)`, `statsTrends()` + types `AttemptSummary`, `Trends`.
- **Progress.tsx**: on view-open fetch `statsTrends` + `historyAttempts`. Empty-state stays when no data. Recharts `LineChart` (y = band 0–9, lines = Writing overall, Speaking overall; dates on x). History list (newest first) → click → fetch detail → open `Dialog` rendering the **existing** Writing/Speaking feedback renderers (exported from their modules; revise/retry button hidden in history mode).
- **Reuse**: export `FeedbackView` (Writing) and `SpeakingFeedback` (Speaking); make their revise/retry callback optional.

## 6. Testing (TDD)
- api: repo save/list/get/trends (SQLite); routes (evaluate→`savedId`; history list/detail; 404; trends shape). Target +~8 tests.
- web: client method tests (mock fetch); Progress renders chart with data and shows empty-state without (ResizeObserver shim already in test-setup). 
- Bands stay labelled "estimate" (existing convention).

## 7. Honesty / boundary
Persistence is purely additive; old routes stay backward-compatible. Progress is a read-only consumer of the 3 new endpoints. Single-user app → `attempts` needs no user_id (consistent with table definition).

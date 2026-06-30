# IELTS Coach v3 — Phase 1 progress ledger

Plan: docs/superpowers/plans/2026-06-29-ielts-v3-phase1.md
Execution: subagent-driven development (fresh implementer per task + review).

## Completed
- Task 1: complete (commit df909d3, scaffold verified by controller — .env untracked, dirs + compose + gitignore correct)
- Task 2: complete (commit 4d8a34a, review clean — app factory/config/errors/health, 1 test passing, .venv untracked)
- Task 3: complete (commit 5fbb513, review clean — 12 models, db session, alembic 0001 via metadata.create_all; 2 tests passing)
- Task 4: complete (commit d0398b2, controller-reviewed repositories.py — all contract signatures correct, camelCase dicts, 6 tests passing)
- Task 5: complete (commit 9946eea, schema validation tests green; full suite 11/11)
- Task 6: complete (commit 53d33f5, fixtures valid + seed_all; 14 tests. Stub keys: generate:{reading B1/B2/C1, listening B1/B2}, score:writing/speaking. seed_sets 5/skill. Concern: listening phone-number keys need lenient grading; stub generate has 3 Qs vs seed 4-5 — downstream must tolerate.)
- Task 7: complete (commit 156d9d9, leveling pure fns; 19 tests. next_band/ielts_to_cefr/cefr_to_ielts/band_params. Note: writing/speaking length mirrors reading — fine.)
- Task 8: complete (commit f9affa7, scoring.py+placement.py; 25 tests. locator_band monotonic verified by controller; grade_placement returns camelCase perSkill/overallBand/cefr/gapToTarget; serve_combo strips answer keys. Timer reads sections.<skill>.seconds, not item sectionSeconds.)
- Task 9: complete (commit ebcbbd1, program.py build_milestones; 28 tests. counts 30/90/180->2/4/6, ends at length_days, no downgrade above target.)
- Task 10: complete (commit 6710114, llm.py stub gateway + prompts.py; 31 tests. generate key "{task}:{skill}:{band}" w/ band fallback; score "score:{task}"; live raises ApiError LLM_UNAVAILABLE; never returns keys. Concern: no vocab/lesson stubs — but those routes are deferred, fine.)
- Task 11: complete (commit ce67f9f, __init__ wiring + onboarding/placement/skills routes; 34 tests. create_app injects REPO+GATEWAY for tests, else inits engine+seed; verified by controller. answers stripped on start; 422 on bad input; health still works.)
- Task 12: complete (commit 8510daa, practice/program/tips routes + repo.serve_any_set/get_latest_program; 40 tests. practice/set falls back to any band; program builds 4 milestones for 90d; tips from fixtures.)
- Task 13: complete (commit 895f751, reading/listening/writing/speaking stub routes; 44 tests. BACKEND COMPLETE — controller re-ran full suite: 44 passed.)

## BACKEND DONE (Tasks 1-13). Frontend in progress (14-21).
- Frontend = React 19 + Vite 6 (NOT 8 — doesn't exist yet) + Tailwind v4 + in-house ui primitives + lucide + Recharts 2.x. Uses api client (Task 14) -> Flask. VITE_API_BASE env (default http://localhost:5050).
- Fonts fall back to system-ui (woff2 self-hosting deferred). No runtime CDN.
- Task 14: complete (commit 242a7af, web scaffold + tokens + typed api client; 2 vitest pass, build compiles. api object in web/src/lib/api/client.ts, types in web/src/lib/types.ts, ApiError class exported.)
- Task 15: complete (commit 4734cbc, ui primitives in web/src/components/ui/ (index.ts re-exports); 5 vitest pass, build clean. MINOR for final review: Toast dismiss button 24px <44px target.)
- Task 16: complete (commit 9268da0, journey.tsx (JourneyProvider/useJourney, Step union, placementResult+milestones state) + Welcome + Onboarding; 7 vitest pass. NOTE for Task 22/final: tsconfig.node.json has TS6306/TS6310 project-ref errors (pre-existing from T14) — npm build via esbuild passes but tsc --noEmit fails; fix tsconfig in T22. App renders placeholders for placement/generating/results/program/milestones/app steps.)
- (Subagent for T16 first paused trying to spawn its own explorer; resumed via SendMessage with 'do not spawn sub-agents' — completed fine. Add this guard to future frontend briefs.)
- Task 17: complete (commit 790b42f, placement runner: TestFrame/PlacementIntro/4 sections/PlacementRunner + App wires "placement"; 8 vitest pass. Submits comboId+answers+writingSamples+speakingText+durationSec -> setPlacementResult -> go("generating"). Speaking = typed fallback.)
- Task 18: complete (commit b52beb7, Generating (polls practiceGenerate/status -> go("results")) + Results (Recharts radar + a11y table + skill cards + CTA go("program")); 10 vitest. Added src/test-setup.ts ResizeObserver shim. Recharts bundle ~599kB (fine).)
- Task 19: complete (commit aab592e, Program (3 RadioCards + gap-based recommendation -> api.program -> setMilestones -> go("milestones")) + Milestones (ordered list of LevelChip targets -> go("app")); 11 vitest.)
- Task 20: complete (commit 3658428, AppShell+Sidebar+BottomTabs+Home+viewContext + App wires "app"; 12 vitest. viewRegistry map structured so T21 swaps placeholders for real skill screens. levels map from api.skillLevels drives nav LevelChips.)
- Task 21: complete (commit 346bcf1, QuizRunner (local grade) + Reading/Listening/Writing/Speaking/Tips/Progress + AppShell swap; 14 vitest. ALL UI DONE. Tips lazy-fetch on expand.)

- Task 22: complete (commit 15916a4, smoke.sh + secret_scan.sh + README + tsconfig fix. VERIFIED FOR REAL: pytest 44/44, vitest 14/14, tsc --noEmit exit 0, secret scan clean, DOCKER SMOKE OK on machine. Fixed: postgres:18 volume path -> /var/lib/postgresql; api fixtures bind-mount (./fixtures:/fixtures:ro); web/api .dockerignore.)

## ALL 22 TASKS COMPLETE. Phase 1 DoD met (docker compose up works offline, full journey, 44+14 tests green). Final whole-branch review next.

## FINAL REVIEW (opus, whole-branch): 0 Critical, 2 Important, 4 Minor — READY.
- Fix commit 3b85cd4: I-1 (route outputs via Pydantic *Out models; PerSkill.assessed; types.ts) + M-1 (toast 44px). Re-verified: api 44/44, web 14/14, tsc clean.
- ACCEPTED Phase-1 deferrals (documented fast-follows, NOT defects):
  - I-2 self-hosted fonts (system-ui fallback by design decision; ship woff2 in a later phase).
  - M-2 web bundle ~630kB (recharts; code-split later).
  - M-3 lenient phone-number grading (revisit with real ASR).
  - M-4 web Dockerfile npm install + dev server (pin npm ci + prod build later).
- tsconfig TS6306/6310 FIXED in T22.

## PHASE 1 COMPLETE & VERIFIED. 23 commits (df909d3..3b85cd4). docker compose up smoke = SMOKE OK on machine.

## PHASE 2a — live LLM wiring (in progress)
Decisions: provider=OpenRouter (OpenAI SDK, base_url https://openrouter.ai/api/v1, OPENROUTER_API_KEY). MODEL_GENERATE=anthropic/claude-haiku-4-5, MODEL_SCORE=anthropic/claude-sonnet-4-6 (OpenRouter slugs — verify live). User HAS a key, wants live test after wiring.
- Implement live branch in api/app/services/llm.py only; stub stays default. generate->MODEL_GENERATE, score->MODEL_SCORE; format prompts from prompts.py; robust JSON parse; never return key; ApiError LLM_UNAVAILABLE on failure.
- Then live verification: user adds OPENROUTER_API_KEY to .env, set LLM_MODE=live, run a real generate + score call.
- DONE (46ac998 + b3a3cf2 + 43ff495): live verified — generate (Haiku) + score (Sonnet) both 200; fixed gunicorn 30s timeout -> 120s.

## PHASE 2b-1 — Writing essay metrics (DONE)
- commit e16e4f6 (impl) + 94fc997 (fix). textstat + LexicalRichness + spaCy/TextDescriptives; NO language-tool/Java; spaCy model baked into image. api 57 tests, web 14.
- Bug fixed: essay_metrics must `import textdescriptives` so its spaCy factories register, else add_pipe E002 -> syntax null in container. Added regression test. Verified live: readability + lexicalDiversity + syntax all populate alongside Sonnet bands.
- Known limitation: MTLD unreliable on short (<~150w) essays (real IELTS essays are 250+w). Not fixed.
- Design polish: pass1 73d40ac, pass2 c250f40, cosmetic 30fef9e. Tools: recommended set already installed (superpowers/security-guidance/atomic-commits/taste skills/built-in code-review).

## PHASE 2b-2 — Speaking ASR (faster-whisper) — DONE
- commits 3fe16bd (api: services/asr.py + POST /api/speaking/transcribe + health asrReady + config ASR_*), b73b15d (web: Recorder component + api.speakingTranscribe multipart + Transcript type), 2ac0203 (requirements faster-whisper==1.1.1 + Dockerfile bakes base model w/ HF_HUB_OFFLINE=1 + log).
- faster-whisper base/cpu/int8; process-level singleton per (model,device,compute); PyAV decodes webm/wav (no system ffmpeg); failures → ApiError ASR_UNAVAILABLE(502) so typed fallback survives. asr_ready() is a cheap find_spec probe (no model load) for /api/health.
- Tests: api 65 (8 new, model mocked), web 15 (1 new client multipart). Live-verified in container: asrReady:true; SAPI sample "...nine o'clock..." → transcript "...9 o'clock..." (200, 5.79s audio); missing file → 422.
- Caveats: per-worker model load (2 gunicorn workers = 2 cold loads, ~9-10s first call each, warm faster); beam_size=5; only transcript feeds examiner (no phoneme/pronunciation scoring yet); .env.example is gitignored (ASR_* documented there locally).
- NEXT staged piece for 2b: none queued. Candidate follow-ups — pronunciation scoring from audio, warm-up at boot or --workers 1 for uniform latency, larger model option.

## PHASE 2c — Attempt persistence + Progress analytics — DONE
- Spec docs/superpowers/specs/2026-06-29-ielts-v3-phase2c-persistence-progress.md (4514bba). Commits 4f6bc44 (api), 7462e79 (web).
- Activates the idle `attempts` table — NO schema change. Repo: save_attempt/list_attempts/get_attempt/trends (bands JSON holds criteria incl overall; criteria JSON holds feedback payload so detail re-renders identically). writing/speaking evaluate now persist + return savedId (additive). New read routes: GET /api/history/attempts?type=, /api/history/attempt/<id> (404), /api/stats/trends.
- web: Progress.tsx = Recharts band-trend (Writing+Speaking overall, sr-only table) + newest-first history → click → Dialog re-renders saved feedback via EXPORTED FeedbackView/SpeakingFeedback (revise/retry now optional). Empty-state kept.
- Tests: api 73 (8 new), web 16 (1 new client). Live-verified in container (LLM_MODE=live): W+S eval → savedId 1,2; trends grouped per skill; history newest-first; detail full payload; 404 ok. NOTE: 2 real sample attempts now in dev pg volume (no delete endpoint yet).
- Audit done this session (full): remaining gaps after 2c → Phase 2d candidates = Mock Test L/R (mocks table idle), R/L practice persistence, guided lessons (lessons table idle), flashcards/vocab (cards table idle), pronunciation scoring from audio, e2e Playwright, deploy. Tables still idle: mocks, lessons, cards.

## PHASE 2d-1 — Guided Lessons — DONE
- Spec docs/superpowers/specs/2026-06-29-ielts-v3-phase2d-guided-lessons.md (7a62938). Commits 6d73255 (api), 2370a16 (web).
- Activates the idle `lessons` table (no schema change). Pure domain lesson_plan.py: pick_focus (weakest skill, plan-weight tiebreak writing>listening>speaking>reading) + current_day (clamp days-since-program-start, 1 if none). Repo get_lesson/save_lesson (upsert by day PK). Routes: GET /api/lesson/today (computed day/focus/band + cached lesson|null), POST /api/lesson/generate (cache-or-generate via gateway "lesson" task; idempotent w/o force; force regenerates), GET /api/lesson/<day>. Offline: 4 lesson stubs (lesson:{skill}:B1, band-fallback) + Day-1 lesson seeded at boot (fixtures/seed_lesson.json).
- web: Session.tsx runner (Teach→Practice→Produce→Review, stepper, auto-check exercises w/ immediate feedback, Generate/Regenerate CTA). viewContext gained "session" view + one-shot prefill (goWithPrefill/consumePrefill); Writing prefills essay, Speaking prefills cue question; Home "Start"→session. client lessonToday/lessonGenerate/lesson + Lesson types.
- Tests: api 84 (11 new), web 20 (4 new). Live-verified: generate (live)→full lesson; today reflects cache; idempotent w/o force; /<day> cached vs null. NOTE: existing dev pg volume predates Day-1 seed (idempotent seed) so today was null there until first generate.
- Tables still idle after 2d-1: mocks, cards. NOT done in 2d-1 (deferred): session "complete"/plan-day tick, full 30-day day-list, Mock Test, flashcards/vocab, pronunciation scoring, e2e Playwright, deploy.

## Batch "lanjut semua berurutan" — remaining 2d basket, sequential. Order: Mock→Pronunciation→Flashcards/Vocab→persist R/L→Playwright→Deploy.
- PHASE 2d-2 Mock Test (L/R) — DONE. commit 3c74419 + log 164bb95. Activates `mocks` table. Repo save_mock/list_mocks; POST/GET /api/mocks. web MockTest.tsx (Test tab, L+R sections, 30-min Timer, local grade, lib/band.ts bandFromPct→approx band, save→Progress). Progress shows mock history. api 86, web 25.
- PHASE 2d-3 Pronunciation — DONE. commit 049f898. Pronounce read-aloud drill: prompts.py pronounce gen+score, routes POST /api/pronounce/sentence + /feedback, stubs. web lib/pron.ts wordAccuracy + Pronounce.tsx (reuses ASR Recorder) + pronounce view + Home link. Approximate (recogniser+tips), no persistence. api 88, web 31.
- PHASE 2d-4 Flashcards+Vocab — DONE. commit ca80edd. Activates LAST idle table `cards`. domain/sm2.py (pure SM-2), repo card ops (tz-safe due), routes /api/cards (+/due, +/<id>/review, DELETE) + /api/vocab + vocab stub. web Vocab.tsx (Build: vocab gen→add; Review: flip→SM-2 grade) + vocab view + Home link. api 95, web 34. Live-verified.
- ALL idle tables now active (attempts, mocks, lessons, cards).
- PHASE 2d-5 persist practice R/L — DONE. commit 3d95039. POST /api/practice/attempt (reading|listening→attempts); trends() now 4 skills; QuizRunner posts score on submit; Progress chart 4 lines, history filtered to w/s. api 96, web 35. Live-verified.
- PHASE 2d-6 Playwright e2e — DONE. commit 44aebbf. @playwright/test + web/playwright.config.ts + web/e2e/journey.spec.ts (3 tests: load smoke, app-shell→Vocab, app-shell→Mock). vitest scoped to src/**. 3/3 e2e green vs compose. IMPORTANT: web Dockerfile COPIES source (no bind-mount) → must `docker compose up -d --build web` after frontend changes (stale UI otherwise; bit us once here).
- PHASE 2d-7 deploy CONFIG — DONE (config only, NOT deployed). commit e0c0d66. web/Dockerfile.prod (vite build→nginx), web/nginx.conf (SPA + /api proxy via docker resolver+var upstream), docker-compose.prod.yml (web published, api+db internal), README Production deploy section. Verified prod web image builds + serves 200. GO-LIVE BLOCKED on owner decision: host (single VPS compose vs split), TLS, access gate (no auth yet), prod secrets/DB creds.
- === BATCH "lanjut semua berurutan" COMPLETE: 2d-2..2d-7 all done. All idle tables active. ===

## PHASE 2e — audit fixes (batch "go"). Order: auth→secretscan→CI→Settings(theme/font)→placement ASR→nav/milestone/a11y.
- 2e-1 Auth passcode gate — DONE 7d81e23. APP_PASSCODE gates /api/* (session cookie); /api/auth/status|login|logout; before_request; PasscodeGate frontend (fails open). api 98, web 37. Live-verified gated 401s.
- 2e-2 Secret-scan fix — DONE 4185e28. Scans only web/dist for key VALUES, real exit code (clean→0, planted→1).
- 2e-3 CI — DONE 3a70cb5. .github/workflows/ci.yml (api pytest + web tsc/vitest/build/secret-scan). e2e stays local.
- 2e-4 Settings theme+font — DONE 6e7f1a3. lib/settings.ts (localStorage, .dark class + --font-* overrides, applied at boot); Settings view (Light/Dark, Default/Dyslexic/Hyperlegible fonts, Lock/logout). Uses the 4 bundled fonts. localStorage shim in test-setup.
- 2e-5 placement ASR — DONE 554895c. placement SpeakingSection uses the Recorder (was coming-soon). PlacementIntro copy updated.
- 2e-6 nav+milestone+a11y — DONE a647920. Sidebar adds Pronounce+Vocab; Home shows real api.milestones (was fake 30%); Progress sr-only table 4 skills. e2e Settings dark-mode test f0fdaff.
- === PHASE 2e COMPLETE (audit fixes). e2e now 4/4 (incl live dark-mode). api 98, web 42. All 26 audit/feature tasks done this session. ===
- Remaining (truly optional, documented): session-complete/plan-day tracking, full 30-day day-list, official raw→band tables, code-split bundle, mobile bottom-tab for new tools, app-level multi-user auth, alembic incremental migrations (currently single create_all). Deploy still awaits owner go-live decision.

## Routes design notes (Tasks 11-13)
- create_app(overrides): if overrides has REPO+GATEWAY -> use them (tests, skip engine). Else init_engine(DATABASE_URL), sessionmaker, seed_all(factory), Repository -> config["REPO"], LlmGateway -> config["GATEWAY"]. APP_CONFIG already set.
- __init__ gets modified by T11, T12, T13 each adding their blueprints (sequential).
- placement/submit: repo.get_combo(comboId) returns FULL items incl. answers (grading); serve_combo (start) strips them. writing_band/speaking_band via GATEWAY.score(...)["bands"]["overall"] when sample present else None. target_band from repo.get_user().target_band. Then set_skill_level per skill + save_placement_attempt.
- skill-levels: repo.get_skill_levels(user.id) -> [{skill,band}] (empty if no user).

## More decisions
- Seed wiring: Task 6 implements seed.py (load_fixture + seed_all(Session)) + authors fixtures + tests (SQLite). Wiring seed_all into create_app startup (after init_engine) happens in Task 11 when __init__ is modified to init engine + repo. Do NOT seed inside the migration.
- Stub gateway keys: generate -> "generate:{skill}:{band}"; score -> "score:{task}". fixtures/stub_responses.json must contain generate:{skill}:{band} for reading+listening at the seeded bands, and score:writing / score:speaking. fixtures/seed_sets.json feeds generated_sets (served via repo.serve_set) — separate from stub_responses.

## Decisions for later tasks
- Task 3 initial migration: use `Base.metadata.create_all(op.get_bind())` in upgrade() (robust offline, no Postgres needed to autogenerate). Task 6 seeds at app startup (create_app after init_engine), NOT in the migration.

## Notes / carried concerns
- postgres:18 used verbatim per spec; if image pull fails at compose-up, fall back to postgres:17.
- Pre-existing logs/ and .claude/launch.json are v1 leftovers, harmless, left in place.

## Remaining
Tasks 2–22 pending.

# pronunciation-drill — 2026-06-29

Phase 2d-3: a read-aloud **Pronounce** drill — show a target sentence, record it (reusing the 2b-2 ASR), get approximate word-match accuracy + missed-word highlighting, then LLM stress/intonation tips.

## What changed
- **api**: `prompts.py` gains `GENERATE_PROMPTS["pronounce"]` (target sentence) + `SCORE_PROMPTS["pronounce"]` (feedback). `routes/pronounce.py`: `POST /api/pronounce/sentence {level?,topic?}` (via `generate("generate", skill="pronounce")`) + `POST /api/pronounce/feedback {target,transcript,accuracy,missed[]}` (via `score("pronounce")`). Offline stubs `generate:pronounce:B1` + `score:pronounce`. Registered.
- **web**: `lib/pron.ts` `wordAccuracy(target, transcript)` (pure, tokenised word-presence match). client `pronounceSentence`/`pronounceFeedback` + types. `components/pronounce/Pronounce.tsx` — target card (missed words underlined wavy after attempt) + `Recorder` reuse + accuracy % + feedback (summary/wordTips/prosody). New `pronounce` view; Home quick link "Pronounce".

## Decisions
- **Approximate, and labelled as such.** Accuracy is browser-recogniser word presence (not phonemes); tips come from the LLM over the target/transcript comparison. Same honesty stance as the v1 Pronounce feature.
- Reuses the ASR `Recorder` — no new audio plumbing.
- No persistence of pronounce attempts in this slice (bounded).

## Verify
- api `pytest -q` → 88 passed (+2). web `npm test` → 31 passed (+6: pron×4, client, smoke); tsc clean; build OK.
- Live: `POST /api/pronounce/sentence` → real target + 3 tips; `POST /api/pronounce/feedback` → summary + wordTips + prosody.

## Caveats
- Word-match accuracy is coarse (presence, not order/phonemes); homophones/insertions aren't penalised.
- Needs a working mic + the ASR server (`asrReady`); otherwise the Recorder shows the typed-only fallback notice and the drill can't score.

## Commits
- `049f898` feat(pronounce): read-aloud pronunciation drill (approx scoring)

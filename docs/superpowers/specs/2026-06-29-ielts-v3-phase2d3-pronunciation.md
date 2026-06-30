# Phase 2d-3 Design: Pronunciation drill (read-aloud)

**Status:** approved (batch) → implementation · **Date:** 2026-06-29

## Goal
A "Pronounce" read-aloud drill: show a target sentence, record it (reusing the 2b-2 ASR transcribe), compute approximate word-match accuracy + highlight missed words, then get LLM stress/intonation tips. Honest approximation (ELSA-style), not phoneme scoring.

## Scope
In: pronounce generate + feedback prompts/routes/stubs; a `Pronounce` view reachable from Speaking + Home; pure word-accuracy helper; reuse `speakingTranscribe`. Out: real phoneme assessment; persistence of pronounce attempts.

## Backend (TDD)
- `prompts.py`: `GENERATE_PROMPTS["pronounce"]` → `{text, focus, tips[]}`; `SCORE_PROMPTS["pronounce"]` → `{summary, wordTips[], prosody[]}`.
- `routes/pronounce.py`: `POST /api/pronounce/sentence {level?,topic?}` → `gateway.generate("generate", skill="pronounce", band=level)`; `POST /api/pronounce/feedback {target,transcript,accuracy,missed[]}` → `gateway.score("pronounce", ...)`. Register blueprint.
- Stubs: `generate:pronounce:B1`, `score:pronounce` in `fixtures/stub_responses.json`.

## Frontend (TDD)
- `lib/pron.ts`: `wordAccuracy(target, transcript) -> {accuracy, missed[]}` — tokenise to lowercase words, accuracy = matched/target count, missed = target words absent from transcript. Pure.
- `client.ts`: `pronounceSentence(body)`, `pronounceFeedback(body)` + `PronounceTarget` / `PronounceFeedback` types.
- `components/pronounce/Pronounce.tsx` (+ `pronounce` view in viewContext/AppShell): show target (seed/generate), Record (reuse `Recorder` → transcript), compute accuracy + highlight missed, call feedback for tips. Reachable via a button on Speaking and a Home quick link.

## Testing
api: pronounce routes return stub shapes (sentence has text/tips; feedback has summary). web: wordAccuracy vectors; client URLs; Pronounce smoke (renders target + record control).

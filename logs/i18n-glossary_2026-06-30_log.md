# i18n-glossary — 2026-06-30

Owner walked through the Indonesian UI and flagged that some English IELTS/technical
terms are left untranslated with no explanation — e.g. "skim" ("apa itu skim?").
Fix: keep the real term (it appears on the actual exam) but **gloss it in Indonesian
in parentheses on first use**.

## What changed (`9d603d3`)
- `fixtures/tips_id.json` — glossed jargon across all four skills:
  - Reading: **Skimming** (baca cepat menyeluruh…), **Scanning** (menyapu teks…),
    **True/False/Not Given** (soal benar/salah/tidak disebutkan), **parafrasa**
    (kalimat diubah susunannya tapi maknanya sama), **Matching Headings**
    (mencocokkan judul dengan paragraf), **bank heading** (daftar pilihan judul).
  - Listening: **parafrasa** gloss, **'no more than TWO words'** (tidak lebih dari
    DUA kata), **Section 1** (bagian pertama).
  - Writing: **prompt** (pernyataan soal), **overview** (ringkasan gambaran umum).
  - Speaking: **cue card** (kartu berisi topik…), and the four criteria glossed —
    Fluency and Coherence (kelancaran & keruntutan), Lexical Resource (kekayaan
    kosakata), Grammatical Range and Accuracy (keragaman & ketepatan tata bahasa),
    Pronunciation (pelafalan); **fluency** → "kelancaran (fluency)".
- `api/app/services/prompts.py` — `lang_note("id")` now also instructs the model:
  when it uses an English IELTS/technical term the learner may not know (skimming,
  collocation, cohesive device, overview, cue card, paraphrase, …), keep the term
  but add a brief Indonesian explanation in parentheses on first use. So AI feedback,
  lessons, and pronunciation tips gloss jargon the same way the fixtures do.

## Verify
- api: `pytest tests/test_i18n_backend.py -q` → 6 passed; `tips_id.json` valid JSON.
- Live (docker compose up --build api): `GET /api/tips/reading` with `X-Lang: id`
  returns the glossed bullets; confirmed in Chrome (Tips → Membaca) that
  "Skimming (baca cepat…)", "Scanning (menyapu teks…)", the T/F/NG gloss, and the
  Matching Headings / bank heading glosses render.

## Notes
- Design boundary unchanged: the official English term stays (learner meets it on
  the real test); only a parenthetical Indonesian explanation is added.
- The AI-side gloss depends on the live model honoring the instruction; fixtures are
  deterministic.

## Commit
- `9d603d3` feat(i18n): gloss IELTS jargon in Indonesian on first use

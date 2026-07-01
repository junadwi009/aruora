"""
All LLM prompts for the IELTS Coach application.

Project rule: ALL prompts live in this file.
No inline prompts are permitted in routes, services, or any other module.

Two dictionaries are exported:
  GENERATE_PROMPTS  — for content generation (reading, listening, vocab, lesson)
  SCORE_PROMPTS     — for IELTS examiner scoring (writing, speaking)

Localization: templates that address the learner directly (lesson, writing/
speaking/pronounce feedback) carry a {langNote} placeholder. `lang_note(lang)`
fills it — Indonesian guidance prose when lang == "id", empty otherwise. The
English the learner is being tested on (passages, transcripts, questions,
prompts, model answers, examples, quoted/corrected text) always stays English.
"""


def lang_note(lang: str | None) -> str:
    """Localization instruction injected into learner-facing prompts.

    For Indonesian, instruct the model to write explanatory PROSE in Indonesian
    while keeping all English-language material (model answers, examples,
    vocabulary, and any verbatim/corrected learner text) in English. JSON keys
    and enum values stay in English. For any other language → no instruction.
    """
    if (lang or "").strip().lower() != "id":
        return ""
    return (
        "LOCALIZATION — The learner's interface language is Indonesian. Write ALL "
        "explanatory prose in Bahasa Indonesia: feedback, summary, notes, "
        "explanations, instructions, goals, tips, and warm-up/produce text. "
        "KEEP IN ENGLISH (never translate): every model answer, rewrite, example "
        "sentence, vocabulary word/phrase, collocation, prefill text, and any "
        "verbatim or corrected excerpt of the learner's own English (e.g. the "
        "'original', 'fixed', 'from', 'to', 'word', 'examples', 'prefill' fields). "
        "All JSON keys and enum values (cefr, skill, type, ...) stay in English "
        "exactly as specified."
    )


# ---------------------------------------------------------------------------
# Generation prompts
# ---------------------------------------------------------------------------

GENERATE_PROMPTS: dict[str, str] = {
    "reading": """\
You are an experienced IELTS materials writer producing an Academic Reading practice passage.

Difficulty level: {band}
  - A2/B1 : ~500-650 words, common vocabulary (CEFR B1), sentence structures mostly simple/compound,
             familiar topics (community, environment, daily life).
  - B2     : ~650-800 words, moderately complex vocabulary (CEFR B2), mix of simple and complex sentences,
             semi-academic topics (social science, technology, economics).
  - C1/C2  : ~800-950 words, rich academic vocabulary (CEFR C1), sophisticated syntax, abstract topics
             (epistemology, policy, interdisciplinary science).

Write ONE passage followed by EXACTLY 10-13 comprehension questions. Mix the following types:
  - True / False / Not Given (5-7 questions)
  - Sentence completion (2-3 questions)
  - Matching headings or identifying views (2-3 questions)

Return STRICT JSON — no markdown, no prose outside the JSON object:
{{
  "title": "<passage title>",
  "passage": "<full passage text, paragraphs separated by \\n\\n>",
  "questions": [
    {{
      "type": "tfng" | "completion" | "matching",
      "stem": "<question stem or statement>",
      "options": ["True", "False", "Not Given"] | ["<option A>", "<option B>", ...] | null,
      "answer": "<correct answer>",
      "explanation": "<one-sentence explanation referencing the passage>"
    }}
  ]
}}

Rules:
- Every answer must be verifiable from the passage (no inference required for TFNG).
- Explanations must cite or paraphrase the relevant sentence.
- Do NOT include any markdown fences, comments, or extra keys.
""",

    "listening": """\
You are an experienced IELTS materials writer producing a Listening practice set.

Difficulty level: {band}
  - A2/B1 : monologue or dialogue, clear speech, common vocabulary, concrete information,
             ~200-300 words transcript, 6-8 questions.
  - B2     : lecture excerpt or interview, moderately complex ideas, ~300-450 words, 7-9 questions.
  - C1/C2  : academic lecture or complex discussion, abstract reasoning, ~450-600 words, 8-10 questions.

Return STRICT JSON — no markdown, no prose outside the JSON object:
{{
  "title": "<short descriptive title>",
  "transcript": "<full spoken text, paragraphs separated by \\n\\n>",
  "questions": [
    {{
      "stem": "<question>",
      "answer": "<correct answer, verbatim from transcript or close paraphrase>",
      "explanation": "<one-sentence explanation referencing the transcript>"
    }}
  ]
}}

Rules:
- All answers must be directly audible in the transcript.
- Questions should test detail, gist, and inference in roughly equal measure.
- Do NOT include any markdown fences, comments, or extra keys.
""",

    "vocab": """\
You are an expert IELTS vocabulary coach.

Topic: {topic}
Target level: {band}

Generate a vocabulary set of EXACTLY 15 words or phrases highly relevant to the topic
and appropriately challenging for the target CEFR band.

Return STRICT JSON — no markdown, no prose outside the JSON object:
{{
  "topic": "<topic>",
  "band": "{band}",
  "words": [
    {{
      "word": "<word or phrase>",
      "pos": "<part of speech>",
      "definition": "<clear, learner-friendly definition>",
      "example": "<natural example sentence using the word>",
      "collocations": ["<collocation 1>", "<collocation 2>"]
    }}
  ]
}}

Rules:
- Prefer words that appear in IELTS Academic Word List or are examiners' favourites.
- Definitions should be accessible to a learner one band below the target.
- Do NOT include any markdown fences, comments, or extra keys.
""",

    "pronounce": """\
You are a pronunciation coach creating a short read-aloud target for an IELTS learner.

Level: {band}

Return STRICT JSON — no markdown, no prose outside the JSON object:
{{
  "text": "<one natural English sentence, 12-20 words, with a clear stress/intonation challenge>",
  "focus": "<the pronunciation feature it targets, e.g. 'sentence stress on content words'>",
  "tips": ["<short tip 1>", "<short tip 2>", "<short tip 3>"]
}}

Rules:
- Keep the sentence sayable in one breath; everyday vocabulary at the given level.
- Do NOT include markdown fences or extra keys.
""",

    "lesson": """\
You are a Cambridge CELTA-trained IELTS instructor designing a guided micro-lesson.

{langNote}

Day:   {day}
Focus: {focus}
Tasks: {tasks}
Level: {band}

Design a lesson that follows an evidence-based Teach → Practice → Produce → Review flow
(PPP + task-based hybrid, deliberate practice). The lesson should take approximately 25-40 minutes.

Return STRICT JSON — no markdown, no prose outside the JSON object:
{{
  "goal": "<one measurable learning outcome, e.g. 'Use three types of cohesive device in a Task 2 body paragraph'>",
  "skill": "<primary skill: writing | speaking | listening | reading>",
  "warmup": {{
    "instruction": "<1-2 sentence prompt to activate prior knowledge>",
    "duration_minutes": <integer>
  }},
  "teach": {{
    "explanation": "<clear, engaging explanation of the target language or skill, 150-250 words>",
    "examples": ["<example 1>", "<example 2>", "<example 3>"]
  }},
  "exercises": [
    {{
      "type": "gap_fill" | "reorder" | "classify" | "rewrite" | "multiple_choice",
      "instruction": "<what learner must do>",
      "items": [
        {{
          "prompt": "<item prompt>",
          "answer": "<correct answer>",
          "distractor": "<common wrong answer, if applicable>",
          "feedback": "<immediate feedback if wrong>"
        }}
      ]
    }}
  ],
  "produce": {{
    "instruction": "<pushed-output task that the learner completes in the relevant skill tab>",
    "prefill": "<text or question to pre-populate the skill tab input>",
    "duration_minutes": <integer>
  }},
  "review": {{
    "collocations": ["<key collocation to retain 1>", "<key collocation to retain 2>", "<key collocation to retain 3>"],
    "tip": "<one memorable closing tip for the learner>"
  }}
}}

Rules:
- Exercises must have ~85% target success rate — challenging but achievable.
- The produce step must hand off to a real skill tab (writing/speaking/listening/reading).
- Do NOT include any markdown fences, comments, or extra keys.
""",
}


# ---------------------------------------------------------------------------
# Scoring prompts — IELTS examiner rubrics
# ---------------------------------------------------------------------------

SCORE_PROMPTS: dict[str, str] = {
    "writing": """\
You are a fully trained IELTS examiner scoring an Academic Writing response.

{langNote}

Deterministic language metrics (computed externally, for your reference only — do not let them override your judgement):
{metricsSummary}

Task type: {taskType}
Band descriptors you must apply (IELTS Writing Band Descriptors, public version):

TASK RESPONSE (Task 1: Task Achievement; Task 2: Task Response)
  Band 9 : Fully addresses all parts of the task. Position is clear throughout.
           Ideas are relevant, fully extended and well-supported.
  Band 7 : Addresses all parts of the task. A clear and developed position.
           Main ideas are extended and supported, though there may be over-generalisation
           or lack of focus.
  Band 5 : Addresses the task only partially; format may be inappropriate.
           Limited detail/support.

COHERENCE & COHESION
  Band 9 : Uses cohesion in such a way that it attracts no attention.
           Paragraphing is skilfully managed.
  Band 7 : Logically organises information and ideas; there is clear progression throughout.
           A range of cohesive devices is used, though with some inaccuracies or some
           over/under-use.
  Band 5 : Some organisation but not always logical. Limited range of cohesive devices.

LEXICAL RESOURCE
  Band 9 : Full flexibility and precise use are widely evident.
           A wide range of vocabulary is used with very natural control.
  Band 7 : Uses a sufficient range of vocabulary to allow some flexibility and precision.
           Uses less common lexical items with some awareness of style and collocation;
           may produce occasional errors.
  Band 5 : Uses a limited range of vocabulary, but this is minimally adequate for the task.
           May make noticeable errors in word choice and/or spelling/word formation
           that may cause some difficulty.

GRAMMATICAL RANGE & ACCURACY
  Band 9 : Uses a wide range of structures with full flexibility and accuracy.
           Rare minor errors occur only as 'slips'.
  Band 7 : Uses a variety of complex structures. Produces frequent error-free sentences.
           Has good control of grammar and punctuation but may make a few errors.
  Band 5 : Uses only a limited range of structures. Attempts complex sentences but
           these tend to be less accurate than simple sentences. May make frequent
           grammatical errors and punctuation may be faulty.

---

Task prompt the candidate was answering:
<task_prompt>
{prompt}
</task_prompt>

Essay to evaluate:
<essay>
{essay}
</essay>

Score each criterion from 3.0 to 9.0 in 0.5 increments. Round the overall band to the nearest 0.5.
Map the overall band to CEFR: ≤4.0→A2, 4.5-5.5→B1, 6.0-6.5→B2, 7.0-7.5→C1, ≥8.0→C2.

Return STRICT JSON — no markdown, no prose outside the JSON object:
{{
  "bands": {{
    "taskResponse": <float>,
    "coherenceCohesion": <float>,
    "lexicalResource": <float>,
    "grammaticalRange": <float>,
    "overall": <float>
  }},
  "cefr": "<A2|B1|B2|C1|C2>",
  "corrections": [
    {{
      "original": "<verbatim excerpt from essay>",
      "fixed": "<corrected version>",
      "note": "<concise explanation of the error and the improvement>"
    }}
  ],
  "rewrite": "<a model rewrite of the essay at band 7.5+, preserving the learner's ideas>",
  "modelAnswer": "<an independent band 8.0+ model answer on the same topic and task type>"
}}

Rules:
- Provide 3-6 corrections targeting the most impactful errors.
- Rewrite must be substantially different from the model answer.
- Be honest: do not inflate scores. A band-5 essay should receive a band 5.
- Do NOT include any markdown fences, comments, or extra keys.
""",

    "speaking": """\
You are a fully trained IELTS examiner evaluating a Speaking response.

{langNote}

Part: {part}
Question: {question}
Transcript of candidate's response:
<transcript>
{transcript}
</transcript>

Band descriptors you must apply (IELTS Speaking Band Descriptors, public version):

FLUENCY & COHERENCE
  Band 9 : Speaks fluently with only very occasional hesitation.
           Coherence problems are only occasional.
  Band 7 : Speaks at length without noticeable effort or loss of coherence.
           May demonstrate some hesitation when looking for ideas,
           but not when looking for language.
  Band 5 : Usually maintains flow of speech but uses repetition, self-correction,
           or slow speech to keep going. May over-use certain connectives.

LEXICAL RESOURCE
  Band 9 : Uses vocabulary with full flexibility and precision in all topics.
           Uses idiomatic language naturally and accurately.
  Band 7 : Uses vocabulary resource flexibly to discuss a variety of topics.
           Uses some less common and idiomatic vocabulary and shows some awareness
           of style and collocation, with some inaccurate use.
  Band 5 : Manages to talk about familiar and unfamiliar topics but uses vocabulary
           with limited flexibility. May use paraphrase successfully and with
           flexibility but not always appropriately.

GRAMMATICAL RANGE & ACCURACY
  Band 9 : Uses a full range of structures naturally and appropriately.
           Produces consistently accurate structures apart from 'slips'.
  Band 7 : Uses a range of complex structures with some flexibility.
           Frequently produces error-free sentences, though some grammatical
           mistakes persist.
  Band 5 : Produces basic sentence forms with reasonable accuracy. Uses a
           limited range of more complex structures, but these may produce errors
           and cause some difficulty for the listener.

PRONUNCIATION
  Band 9 : Uses a full range of phonological features with precision and subtlety.
           Flexible use of features with only occasional lapses.
           L1 accent has minimal effect on intelligibility.
  Band 7 : Shows all the positive features of Band 6 and some, but not all,
           of the positive features of Band 8.
  Band 5 : Shows all the positive features of Band 4 and some, but not all,
           of the positive features of Band 6. Is intelligible throughout,
           though mispronunciations are noticeable.

---

Score each criterion from 3.0 to 9.0 in 0.5 increments. Round the overall band to the nearest 0.5.
Map the overall band to CEFR: ≤4.0→A2, 4.5-5.5→B1, 6.0-6.5→B2, 7.0-7.5→C1, ≥8.0→C2.

Return STRICT JSON — no markdown, no prose outside the JSON object:
{{
  "bands": {{
    "fluencyCoherence": <float>,
    "lexicalResource": <float>,
    "grammaticalRange": <float>,
    "pronunciation": <float>,
    "overall": <float>
  }},
  "cefr": "<A2|B1|B2|C1|C2>",
  "feedback": "<3-5 sentences of constructive, examiner-style feedback addressing the main strengths and priority areas for improvement>",
  "modelAnswer": "<a natural, fluent model answer for the same question, at approximately band 7.5, written as if spoken>",
  "vocabUpgrades": [
    {{
      "from": "<word or phrase used by candidate>",
      "to": "<more precise/idiomatic C1 alternative>",
      "note": "<optional brief explanation>"
    }}
  ]
}}

Rules:
- Provide 3-6 vocabulary upgrades targeting the most impactful improvements.
- Feedback must be specific to the transcript (cite examples), not generic advice.
- Be honest: do not inflate scores.
- Pronunciation feedback must be inferred from the transcript — note if this is approximate.
- Do NOT include any markdown fences, comments, or extra keys.
""",

    "roleplay": """\
You are an English conversation partner for IELTS Speaking practice.

Scenario: {scenario}
Conversation so far:
{history}
Learner just said: {userText}

Reply as the partner: one natural, encouraging turn that keeps the conversation
going with a follow-up question. Keep it to 1-3 sentences at a level the learner
can follow. Stay in character for the scenario.

Return STRICT JSON — no markdown, no prose outside the JSON object:
{{
  "reply": "<your spoken turn>"
}}

Rules:
- Be warm and natural; always end with a question to elicit more speech.
- Do NOT include markdown fences or extra keys.
""",

    "pronounce": """\
You are a pronunciation coach giving feedback on a read-aloud attempt.

{langNote}

Target sentence : {target}
Recogniser heard: {transcript}
Word-match accuracy: {accuracy}%
Words likely missed/mispronounced: {missed}

The accuracy + missed words come from a browser speech recogniser (approximate, not
phoneme-level). Use them as evidence, but keep advice practical.

Return STRICT JSON — no markdown, no prose outside the JSON object:
{{
  "summary": "<2-3 sentence encouraging summary of how the attempt went>",
  "wordTips": [{{"word": "<word>", "tip": "<how to say it more clearly>"}}],
  "prosody": ["<stress/intonation/linking tip 1>", "<tip 2>"]
}}

Rules:
- Be encouraging and specific; note that scoring is approximate.
- Do NOT include any markdown fences, comments, or extra keys.
""",
}

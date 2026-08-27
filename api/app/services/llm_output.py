"""WS05-02 — Server-side structured output schemas for every LLM task.

``json.loads`` is parsing, not semantic validation. Every gateway response is
validated against the Pydantic model below BEFORE it reaches routes,
persistence, or rendering. Validation failure is a controlled
``LLM_BAD_OUTPUT`` error — partially valid scores are never persisted.

Design rules enforced here:
- numeric bands stay inside the legal product range and 0.5 increments;
- learner-facing lists are bounded (corrections/questions/words/exercises…);
- every string is length-capped and stripped of Unicode C0 control characters;
- unknown/privileged model-added fields are DROPPED (never rendered/persisted);
- generated question schemas include their answers (server-side grading /
  reveal-time data), so nothing here implies the client may receive them.

Prompt-injection resistance is NOT claimed: these bounds prove contract
integrity only (see tests/test_prompt_injection.py).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationError

from app.errors import ApiError

_C0_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_HALF_BANDS = [round(3.0 + 0.5 * i, 1) for i in range(13)]


class _Strict(BaseModel):
    # Unknown model fields are removed rather than forwarded anywhere.
    model_config = ConfigDict(extra="ignore", validate_assignment=False)

    @field_validator("*", mode="before")
    @classmethod
    def _strip_control_chars(cls, v):
        if isinstance(v, str):
            return _C0_RE.sub("", v)
        if isinstance(v, list):
            return [_C0_RE.sub("", x) if isinstance(x, str) else x for x in v]
        return v


def _half_band_ok(v: float) -> float:
    if not any(abs(v - b) < 1e-9 for b in _HALF_BANDS):
        raise ValueError("band scores must be on 0.5 increments within 3.0–9.0")
    return v


class _BandsCore(_Strict):
    overall: float

    @field_validator("overall")
    @classmethod
    def _ov(cls, v):
        return _half_band_ok(float(v))


class WritingBands(_BandsCore):
    taskResponse: float
    coherenceCohesion: float
    lexicalResource: float
    grammaticalRange: float

    @field_validator("taskResponse", "coherenceCohesion", "lexicalResource",
                     "grammaticalRange")
    @classmethod
    def _crits(cls, v):
        return _half_band_ok(float(v))


class SpeakingBands(_BandsCore):
    fluencyCoherence: float
    lexicalResource: float
    grammaticalRange: float
    # WS02-04: transcript-only evidence cannot score pronunciation. The model
    # may still illegally emit a number; the route-level normaliser strips it
    # AFTER this schema passes (see scoring.normalize_speaking_estimate).
    pronunciation: float | str

    @field_validator("fluencyCoherence", "lexicalResource", "grammaticalRange")
    @classmethod
    def _crits(cls, v):
        return _half_band_ok(float(v))


class Correction(_Strict):
    original: str = Field(min_length=1, max_length=400)
    fixed: str = Field(min_length=1, max_length=400)
    note: str = Field(default="", max_length=600)


class WritingScoreOut(_Strict):
    bands: WritingBands
    cefr: str = Field(pattern=r"^(A2|B1|B2|C1|C2)$")
    corrections: list[Correction] = Field(max_length=8)
    rewrite: str = Field(max_length=20000)
    modelAnswer: str = Field(max_length=20000)


class VocabUpgrade(_Strict):
    from_: str = Field(alias="from", min_length=1, max_length=120)
    to: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=400)

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class SpeakingScoreOut(_Strict):
    bands: SpeakingBands
    cefr: str = Field(pattern=r"^(A2|B1|B2|C1|C2)$")
    feedback: str = Field(min_length=1, max_length=4000)
    modelAnswer: str = Field(max_length=20000)
    vocabUpgrades: list[VocabUpgrade] = Field(default_factory=list, max_length=8)


class QuestionItem(_Strict):
    stem: str = Field(min_length=1, max_length=500)
    options: list[str] | None = Field(default=None, max_length=6)
    answer: str = Field(min_length=1, max_length=300)
    explanation: str = Field(default="", max_length=700)
    type: str | None = None

    @field_validator("options")
    @classmethod
    def _opt_len(cls, v):
        if v:
            for o in v:
                if not o or len(o) > 120:
                    raise ValueError("option empty or too long")
        return v


class ReadingSetOut(_Strict):
    title: str = Field(min_length=1, max_length=200)
    passage: str = Field(min_length=1, max_length=22000)
    questions: list[QuestionItem] = Field(min_length=1, max_length=20)


class ListeningSetOut(_Strict):
    title: str = Field(min_length=1, max_length=200)
    transcript: str = Field(min_length=1, max_length=14000)
    questions: list[QuestionItem] = Field(min_length=1, max_length=15)


class WordItem(_Strict):
    word: str = Field(min_length=1, max_length=80)
    pos: str = Field(default="", max_length=40)
    definition: str = Field(default="", max_length=400)
    example: str = Field(default="", max_length=300)
    collocations: list[str] = Field(default_factory=list, max_length=6)

    @field_validator("collocations")
    @classmethod
    def _coll(cls, v):
        return [c[:80] for c in v]


class VocabSetOut(_Strict):
    topic: str = Field(default="", max_length=160)
    band: str = Field(default="", max_length=6)
    words: list[WordItem] = Field(min_length=1, max_length=20)


class LessonExerciseItem(_Strict):
    prompt: str = Field(min_length=1, max_length=400)
    answer: str = Field(min_length=1, max_length=400)
    distractor: str = Field(default="", max_length=400)
    feedback: str = Field(default="", max_length=400)


class LessonExercise(_Strict):
    type: str = Field(pattern=r"^(gap_fill|reorder|classify|rewrite|multiple_choice)$")
    instruction: str = Field(min_length=1, max_length=400)
    items: list[LessonExerciseItem] = Field(min_length=1, max_length=12)


class LessonOut(_Strict):
    goal: str = Field(min_length=1, max_length=300)
    skill: str = Field(pattern=r"^(writing|speaking|listening|reading)$")
    warmup: dict
    teach: dict
    exercises: list[LessonExercise] = Field(min_length=1, max_length=10)
    produce: dict
    review: dict


class PronounceTargetOut(_Strict):
    text: str = Field(min_length=1, max_length=240)
    focus: str = Field(default="", max_length=140)
    tips: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("tips")
    @classmethod
    def _tips(cls, v):
        return [t[:200] for t in v]


class PronounceTip(_Strict):
    word: str = Field(min_length=1, max_length=60)
    tip: str = Field(min_length=1, max_length=200)


class PronounceFeedbackOut(_Strict):
    summary: str = Field(min_length=1, max_length=800)
    wordTips: list[PronounceTip] = Field(default_factory=list, max_length=8)
    prosody: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("prosody")
    @classmethod
    def _pros(cls, v):
        return [p[:240] for p in v]


class RoleplayTurnOut(_Strict):
    reply: str = Field(min_length=1, max_length=1200)


# Task name → schema. Both real prompts (SCORE_PROMPTS / GENERATE_PROMPTS) and
# fake gateways used by pool code are validated through this single map.
OUTPUT_SCHEMAS: dict[str, type[_Strict]] = {
    "writing": WritingScoreOut,
    "speaking": SpeakingScoreOut,
    "reading": ReadingSetOut,
    "listening": ListeningSetOut,
    "vocab": VocabSetOut,
    "lesson": LessonOut,
    "pronounce": PronounceFeedbackOut,
    "pronounce_target": PronounceTargetOut,
    "roleplay": RoleplayTurnOut,
}


def resolve_schema(task: str, *, generate: bool = False) -> type[_Strict]:
    """Schema for *task*. Generation tasks reaching OUTPUT_SCHEMAS under their
    skill name (reading/listening/vocab/pronounce/lesson) reuse that key."""
    if task in OUTPUT_SCHEMAS:
        return OUTPUT_SCHEMAS[task]
    raise ApiError(
        "LLM_BAD_OUTPUT",
        f"No output contract registered for task {task!r}",
        502,
    )


def validate_llm_output(task: str, payload) -> dict:
    """Validate an untrusted model response against *task*'s schema.

    Returns the cleaned dict (unknown/privileged fields dropped, control chars
    stripped). Raises ApiError('LLM_BAD_OUTPUT') on invalid shapes — callers
    must treat it like any other deterministic provider rejection (no retry,
    no partial persistence).
    """
    if not isinstance(payload, dict):
        raise ApiError("LLM_BAD_OUTPUT", "model output was not a JSON object", 502)
    schema = resolve_schema(task)
    try:
        return schema.model_validate(payload).model_dump(by_alias=True)
    except ValidationError as e:
        first = e.errors()[:3]
        detail = "; ".join(
            ".".join(str(p) for p in err.get("loc", [])) + ": " + err.get("msg", "")
            for err in first
        )
        raise ApiError(
            "LLM_BAD_OUTPUT",
            f"model output failed contract for {task!r}: {detail}",
            502,
        )

"""Pydantic v2 request/response contracts for the IELTS Coach API.

Wire format: camelCase JSON.
Python attributes: snake_case.
All models use Field aliases for camelCase keys + populate_by_name=True so
routes can construct models with either the alias or the Python name.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Enums / Literals
# ---------------------------------------------------------------------------

Goal = Literal["work", "study_abroad", "other"]
Cefr = Literal["A1A2", "B1", "B2", "C1", "C2"]
Skill = Literal["listening", "reading", "writing", "speaking"]
ProgramLength = Literal[30, 90, 180]


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class OnboardingIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1)
    goal: Goal
    target_band: float = Field(alias="targetBand", ge=4.0, le=9.0)
    skill_targets: dict = Field(alias="skillTargets", default_factory=dict)
    # WS23: optional deadline captured as exam month (YYYY-MM) or full date.
    exam_date: str | None = Field(
        alias="examDate", default=None,
        pattern=r"^\d{4}-\d{2}(-\d{2})?$",
    )


class PlacementSubmitIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    combo_id: int = Field(alias="comboId")
    answers: dict
    writing_samples: dict = Field(alias="writingSamples", default_factory=dict)
    speaking_text: str | None = Field(alias="speakingText", default=None)
    duration_sec: int = Field(alias="durationSec", default=0)


class ProgramIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    length_days: ProgramLength = Field(alias="lengthDays")


# ---------------------------------------------------------------------------
# WS09-03B: request contracts for LLM/ASR/persistence surfaces.
# Lengths are defensive static ceilings; routes may enforce tighter
# config-driven bounds (cfg.MAX_*_CHARS) on top. Unknown fields are ignored
# and never reach prompts, persistence, or analytics.
# ---------------------------------------------------------------------------


class WritingEvaluateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    essay: str = ""
    task_type: str | None = Field(alias="taskType", default=None, max_length=64)
    prompt: str | None = Field(default=None, max_length=4000)


class SpeakingEvaluateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    transcript: str = ""
    part: str | None = Field(default=None, max_length=64)
    question: str | None = Field(default=None, max_length=1000)
    # WS06-06: the client's own ASR job id — its SERVER-side acoustic features
    # (never client-supplied metrics) are attached to the stored attempt.
    asrJobId: str | None = Field(default=None, max_length=64)


class RoleplayTurn(BaseModel):
    role: str = Field(default="", max_length=32)
    text: str = Field(default="", max_length=1200)


class SpeakingRoleplayIn(BaseModel):
    scenario: str = Field(default="casual conversation", max_length=512)
    history: list[RoleplayTurn] = Field(default_factory=list, max_length=24)
    user_text: str = Field(alias="userText", default="", max_length=1200)


class BandGenerateIn(BaseModel):
    """Body of reading/listening set requests. Strict band validation stays in
    routes._gencap.check_band (single source of truth for allowed values)."""

    band: str | None = Field(default=None, max_length=16)


class VocabIn(BaseModel):
    topic: str = Field(default="general", max_length=200)
    level: str | None = Field(default="B1", max_length=16)


class PronounceSentenceIn(BaseModel):
    level: str | None = Field(default="B1", max_length=16)
    topic: str | None = Field(default=None, max_length=200)


class PronounceFeedbackIn(BaseModel):
    target: str = Field(default="", max_length=240)
    transcript: str = ""
    accuracy: float = Field(default=0, ge=0, le=100)
    missed: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def _cap_missed_items(self):
        self.missed = [str(m)[:64] for m in self.missed]
        return self


class LessonGenerateIn(BaseModel):
    day: int | None = Field(default=None, ge=1, le=400)
    focus: str | None = Field(default=None, max_length=200)
    band: str | None = Field(default=None, max_length=16)
    force: bool = False


def _half_band_ok(v: float) -> bool:
    return 0.0 <= v <= 9.0 and abs(v * 2 - round(v * 2)) < 1e-9


class MockSaveIn(BaseModel):
    """IELTS Listening/Reading mock scores: whole/half bands only."""

    listening: float
    reading: float
    overall: float

    @model_validator(mode="after")
    def _bands(self):
        for name in ("listening", "reading", "overall"):
            v = getattr(self, name)
            if not _half_band_ok(v):
                raise ValueError(f"{name} must be a half-band score between 0 and 9")
        return self


class PracticeAttemptIn(BaseModel):
    skill: Literal["reading", "listening"]
    correct: int = Field(ge=0)
    total: int = Field(ge=1)
    band: float = Field(default=0.0, ge=0.0, le=9.0)
    title: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _correct_le_total(self):
        if self.correct > self.total:
            raise ValueError("correct cannot exceed total")
        return self


class FlashcardIn(BaseModel):
    front: str = Field(min_length=1, max_length=1000)
    back: str = Field(min_length=1, max_length=1000)


class CardAddIn(BaseModel):
    front: str | None = Field(default=None, max_length=1000)
    back: str | None = Field(default=None, max_length=1000)
    cards: list[FlashcardIn] | None = Field(default=None, max_length=100)


class CardReviewIn(BaseModel):
    quality: int = Field(ge=0, le=5)


class PasscodeLoginIn(BaseModel):
    passcode: str = Field(default="", max_length=256)


class GateHeartbeatIn(BaseModel):
    seconds: int | None = Field(default=None, ge=0, le=7200)


class GateUnlockIn(BaseModel):
    stars: int = Field(default=0, ge=1, le=5)
    insight: str = Field(default="", max_length=2000)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PlacementStartOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    combo_id: int = Field(alias="comboId")
    sections: dict
    target_minutes: int = Field(alias="targetMinutes")
    items: list = []


class PerSkill(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cefr: Cefr
    ielts: float | None = None
    ielts_approx: float | None = Field(alias="ieltsApprox", default=None)
    raw: str | None = None
    confidence: str | None = None
    assessed: bool | None = None
    criteria: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)


class PlacementResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    per_skill: dict[str, PerSkill] = Field(alias="perSkill")
    overall_band: float = Field(alias="overallBand")
    cefr: Cefr
    gap_to_target: float = Field(alias="gapToTarget")


class MilestoneOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    idx: int
    day_target: int = Field(alias="dayTarget")
    title: str
    targets: dict


class ProgramOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    program: dict
    milestones: list[MilestoneOut]


class OnboardingOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    goal: Goal
    target_band: float = Field(alias="targetBand")
    skill_targets: dict = Field(alias="skillTargets", default_factory=dict)


class SkillLevelOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    skill: Skill
    band: Cefr


class GenerateJobOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(alias="jobId")


class JobStatusOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    done: bool
    progress: int


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    "Goal",
    "Cefr",
    "Skill",
    "ProgramLength",
    "OnboardingIn",
    "OnboardingOut",
    "PlacementSubmitIn",
    "ProgramIn",
    "WritingEvaluateIn",
    "SpeakingEvaluateIn",
    "SpeakingRoleplayIn",
    "RoleplayTurn",
    "BandGenerateIn",
    "VocabIn",
    "PronounceSentenceIn",
    "PronounceFeedbackIn",
    "LessonGenerateIn",
    "MockSaveIn",
    "PracticeAttemptIn",
    "FlashcardIn",
    "CardAddIn",
    "CardReviewIn",
    "PasscodeLoginIn",
    "GateHeartbeatIn",
    "GateUnlockIn",
    "PlacementStartOut",
    "PerSkill",
    "PlacementResultOut",
    "MilestoneOut",
    "ProgramOut",
    "SkillLevelOut",
    "GenerateJobOut",
    "JobStatusOut",
]

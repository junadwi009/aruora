"""
WS20 — Readiness contract engine (deterministic, no percentages).

`Readiness` is NOT a second IELTS score (20 §Readiness contract):
- a percentage such as "68% ready" is PROHIBITED until a validated formula
  exists; this engine emits the clearer estimate/gap/priority/coverage
  construct instead;
- every field is explainable from learner state (latest per-skill practice
  estimates stored server-side);
- the method version travels with the payload so the product can evolve the
  heuristic without silently changing meaning;
- CEFR alignment elsewhere stays approximate (WS02); nothing here claims
  official equivalence.

Pure domain: no I/O. Callers supply the latest per-skill estimates.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.scoring import ielts_round_half_band

READINESS_METHOD_VERSION = "readiness-v0"

SKILLS = ("listening", "reading", "writing", "speaking")

_DISCLAIMER = (
    "Practice estimates only — not an official IELTS result. "
    "CEFR alignment is approximate."
)


def build_readiness(
    skill_estimates: dict[str, float | None],
    target_band: float,
    *,
    skill_targets: dict[str, float] | None = None,
    now: datetime | None = None,
) -> dict:
    """
    Build the readiness summary.

    Parameters
    ----------
    skill_estimates : per-skill latest overall practice estimate (or None when
        a skill has never been assessed).
    target_band : overall target from the profile.
    skill_targets : optional per-skill targets overriding target_band for gap
        ranking.
    """
    targets = {s: float(skill_targets.get(s, target_band)) for s in SKILLS} \
        if skill_targets else {s: float(target_band) for s in SKILLS}

    assessed: dict[str, float] = {
        s: float(v) for s, v in skill_estimates.items()
        if s in SKILLS and isinstance(v, (int, float))
    }
    coverage = {
        "assessed": len(assessed),
        "total": len(SKILLS),
        "complete": len(assessed) == len(SKILLS),
        "missing": [s for s in SKILLS if s not in assessed],
    }

    current_estimate = None
    if assessed:
        current_estimate = ielts_round_half_band(
            sum(assessed.values()) / len(assessed)
        )

    gaps: dict[str, float] = {
        s: round(targets[s] - v, 2) for s, v in assessed.items()
    }
    priority_skill = None
    if gaps:
        priority_skill = max(gaps, key=lambda s: gaps[s])

    return {
        "method": READINESS_METHOD_VERSION,
        "generatedAt": (now or datetime.now(timezone.utc))
        .isoformat(),
        "targetBand": float(target_band),
        "skillTargets": {s: targets[s] for s in SKILLS},
        "currentEstimate": current_estimate,
        "gap": (round(targets[priority_skill] - assessed[priority_skill], 2)
                if priority_skill else None),
        "prioritySkill": priority_skill,
        "perSkill": {
            s: {
                "estimate": assessed.get(s),
                "target": targets[s],
                "gap": (round(targets[s] - assessed[s], 2)
                        if s in assessed else None),
                "assessed": s in assessed,
            }
            for s in SKILLS
        },
        "evidenceCoverage": coverage,
        "estimateBasis": "mean of the learner's latest per-skill practice estimates",
        "disclaimer": _DISCLAIMER,
    }

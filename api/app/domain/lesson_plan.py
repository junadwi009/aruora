"""
Pure helpers that decide *what* today's guided lesson should be — which skill to
focus on and which program day we're on. No I/O, no LLM; trivially testable.
"""
from __future__ import annotations

from datetime import date, datetime

from app.domain.leveling import BANDS

# Tie-break order when two skills share the lowest band — mirrors the 30-day
# plan's time weighting (Writing 35% · Listening 30% · Speaking 25% · Reading 10%).
_PLAN_PRIORITY = ["writing", "listening", "speaking", "reading"]


def pick_focus(skill_levels: list[tuple[str, str]]) -> str:
    """Return the weakest skill (lowest CEFR band); ties broken by plan weight.

    `skill_levels` is a list of (skill, band) pairs. Falls back to "writing"
    (highest-weight skill) when nothing is known yet.
    """
    if not skill_levels:
        return "writing"

    def rank(item: tuple[str, str]) -> tuple[int, int]:
        skill, band = item
        band_idx = BANDS.index(band) if band in BANDS else len(BANDS)
        prio = _PLAN_PRIORITY.index(skill) if skill in _PLAN_PRIORITY else len(_PLAN_PRIORITY)
        return (band_idx, prio)

    return min(skill_levels, key=rank)[0]


def current_day(start_date, length_days, today: date) -> int:
    """Clamp (days since program start + 1) into [1, length_days]. 1 if no program."""
    if start_date is None or not length_days:
        return 1
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    day = (today - start_date).days + 1
    return max(1, min(day, length_days))

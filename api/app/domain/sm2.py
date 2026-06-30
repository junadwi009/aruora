"""
SM-2 spaced-repetition scheduling (pure). Returns the next card state given the
review quality. No I/O — the repository applies the result and sets the due date.

quality 0-5 (UI maps Again=1, Hard=3, Good=4, Easy=5). q < 3 = a lapse.
"""
from __future__ import annotations

_MIN_EASE = 1.3


def schedule(ease: float, interval: int, reps: int, lapses: int, quality: int) -> dict:
    q = max(0, min(5, int(quality)))

    if q < 3:
        # Lapse: relearn from the start tomorrow.
        new_reps = 0
        new_interval = 1
        new_lapses = lapses + 1
    else:
        new_reps = reps + 1
        if reps == 0:
            new_interval = 1
        elif reps == 1:
            new_interval = 6
        else:
            new_interval = round(interval * ease)
        new_lapses = lapses

    # SM-2 ease update, floored at 1.3.
    new_ease = ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    if new_ease < _MIN_EASE:
        new_ease = _MIN_EASE

    return {
        "ease": round(new_ease, 3),
        "interval": new_interval,
        "reps": new_reps,
        "lapses": new_lapses,
    }

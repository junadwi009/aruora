"""
Domain layer — placement scoring pure functions.
No I/O.  All inputs/outputs are plain Python values.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.domain.leveling import BANDS


def locator_band(
    tier_results: dict[str, tuple[int, int]],
    pass_threshold: float = 0.667,
) -> str:
    """
    Determine the highest CEFR band at which the user passes.

    Rules
    -----
    - Iterate tiers in BANDS order (low → high: A1A2, B1, B2, C1, C2).
    - A tier "passes" if:
        * total == 0  (no items → treated as passed/skipped), OR
        * correct / total >= pass_threshold
    - Placement = the HIGHEST band such that that band AND every lower band pass
      (monotonic: once a tier fails, stop advancing).
    - If A1A2 fails → return "A1A2" (floor rule).

    Parameters
    ----------
    tier_results : dict mapping band label → (correct, total)
    pass_threshold : fraction required to pass (default 2/3 ≈ 0.667)

    Returns
    -------
    The placed CEFR band string, e.g. "B2".
    """
    placement = BANDS[0]  # floor: A1A2

    for band in BANDS:
        if band not in tier_results:
            # band not present in results — treat as skipped (pass)
            placement = band
            continue

        correct, total = tier_results[band]

        if total == 0:
            # No items for this tier — treated as passed
            placement = band
        elif correct / total >= pass_threshold:
            # Tier passes — advance placement
            placement = band
        else:
            # Tier fails — stop here (monotonic rule)
            break

    return placement


def ielts_round_half_band(score: float) -> float:
    """
    Round a score to the nearest 0.5 per IELTS official rules.

    IELTS rounds the average of 4 skills to the nearest half-band.
    Quarter bands (.25 and .75) always round UP (not banker's rounding).

    Examples:
    - 6.25 → 6.5
    - 6.75 → 7.0
    - 6.125 → 6.0
    - 3.875 → 4.0
    - 6.0 → 6.0
    - 6.5 → 6.5
    """
    return float((Decimal(str(score)) * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 2)


def overall_band(skill_bands: dict[str, float]) -> float:
    """
    Compute the overall IELTS band from per-skill numeric scores.

    Uses IELTS official rounding: round to nearest 0.5 with ties rounding UP.
    """
    values = list(skill_bands.values())
    mean = sum(values) / len(values)
    return ielts_round_half_band(mean)


# WS02-04: transcript-only evidence cannot assess pronunciation.
# These are the criteria assessable from a text transcript alone.
SPEAKING_TEXT_CRITERIA = ("fluencyCoherence", "lexicalResource", "grammaticalRange")
SPEAKING_PRONUNCIATION_UNASSESSED = "unassessed"


def normalize_speaking_estimate(result: dict) -> dict:
    """
    Enforce WS02-04 on a Speaking estimate produced from transcript-only input.

    - Pronunciation can NEVER be scored from text: force it to "unassessed"
      regardless of what the model returned (fail closed on fabrication).
    - The overall band must not be an examiner-like mean that includes a
      fabricated pronunciation criterion: recompute it as the officially
      rounded mean of the text-assessable criteria only.

    Mutates and returns *result*.
    """
    bands = result.get("bands")
    if not isinstance(bands, dict):
        return result

    # Fail closed: strip any fabricated pronunciation score.
    bands["pronunciation"] = SPEAKING_PRONUNCIATION_UNASSESSED

    nums = [
        float(bands[c])
        for c in SPEAKING_TEXT_CRITERIA
        if isinstance(bands.get(c), (int, float))
    ]
    if nums:
        bands["overall"] = ielts_round_half_band(sum(nums) / len(nums))
    return result

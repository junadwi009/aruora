"""
Domain layer — placement test grading and combo serving.

Pure functions (grade_placement, grade_skill_locator, normalize_answer).
serve_combo takes a repo but is otherwise stateless.
"""

from __future__ import annotations

import random
import re

from app.domain.leveling import BANDS, cefr_to_ielts, ielts_to_cefr, ielts_to_cefr_approx
from app.domain.scoring import locator_band, overall_band


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_answer(s) -> str:
    """
    Lenient normalisation for L/R grading:
      - lowercase
      - strip leading/trailing whitespace
      - collapse internal whitespace runs to a single space
      - remove spaces inside digit groups (so "0207 946 0958" == "020 7946 0958")
    """
    if s is None:
        return ""
    text = str(s).lower().strip()
    # Remove spaces between digit sequences (phone-number tolerance)
    text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    # Collapse remaining internal whitespace
    text = re.sub(r"\s+", " ", text)
    return text


# ---------------------------------------------------------------------------
# Skill-level locator grader
# ---------------------------------------------------------------------------

def grade_skill_locator(
    items: list[dict],
    answers: dict,
) -> tuple[str, str, str]:
    """
    Grade a set of locator items for a single skill.

    Parameters
    ----------
    items : list of dicts, each with keys:
        id, skill, bandTag, payload (containing "answer" key)
    answers : maps str(item_id) -> user_answer string

    Returns
    -------
    (cefr_band, raw_str, confidence)
      cefr_band   : e.g. "B2"
      raw_str     : e.g. "7/10"
      confidence  : "low" if ALL correct or ALL wrong, else "medium"
    """
    # Group items by bandTag
    tier_correct: dict[str, int] = {}
    tier_total: dict[str, int] = {}

    for item in items:
        band = item["bandTag"]
        tier_total[band] = tier_total.get(band, 0) + 1

        item_id = str(item["id"])
        user_ans = normalize_answer(answers.get(item_id, ""))
        correct_ans = normalize_answer(item.get("payload", {}).get("answer", ""))

        if user_ans == correct_ans:
            tier_correct[band] = tier_correct.get(band, 0) + 1
        else:
            tier_correct.setdefault(band, 0)

    tier_results: dict[str, tuple[int, int]] = {
        band: (tier_correct.get(band, 0), tier_total[band])
        for band in tier_total
    }

    cefr_band = locator_band(tier_results)

    total_correct = sum(tier_correct.values())
    total_items = sum(tier_total.values())
    raw_str = f"{total_correct}/{total_items}"

    # Confidence: "low" if all correct (ceiling) or all wrong (floor)
    if total_correct == total_items or total_correct == 0:
        confidence = "low"
    else:
        confidence = "medium"

    return cefr_band, raw_str, confidence


# ---------------------------------------------------------------------------
# Full placement grader
# ---------------------------------------------------------------------------

def grade_placement(
    combo: dict,
    answers: dict,
    writing_band: float | None,
    speaking_band: float | None,
    target_band: float,
) -> dict:
    """
    Grade a completed placement combo.

    Parameters
    ----------
    combo        : dict returned by repo.get_combo (or same shape)
    answers      : maps str(item_id) -> user_answer
    writing_band : IELTS float if assessed, else None
    speaking_band: IELTS float if assessed, else None
    target_band  : user's target IELTS band (e.g. 6.5)

    Returns
    -------
    camelCase dict:
    {
      "perSkill": {
        "listening": {"cefr", "ieltsApprox", "raw", "confidence"},
        "reading":   {"cefr", "ieltsApprox", "raw", "confidence"},
        "writing":   {"cefr", "ielts"},
        "speaking":  {"cefr", "ielts"},
      },
      "overallBand": float,
      "cefr": str,
      "gapToTarget": float,
    }
    """
    items = combo.get("items", [])
    listening_items = [it for it in items if it["skill"] == "listening"]
    reading_items = [it for it in items if it["skill"] == "reading"]

    # Grade listening
    l_cefr, l_raw, l_conf = grade_skill_locator(listening_items, answers)
    l_lo, l_hi = cefr_to_ielts(l_cefr)
    l_num = (l_lo + l_hi) / 2.0

    # Grade reading
    r_cefr, r_raw, r_conf = grade_skill_locator(reading_items, answers)
    r_lo, r_hi = cefr_to_ielts(r_cefr)
    r_num = (r_lo + r_hi) / 2.0

    # Writing
    if writing_band is not None:
        w_cefr = ielts_to_cefr(writing_band)
        w_ielts = writing_band
        w_num = writing_band
    else:
        # Conservative estimate: lower of L/R cefr bands
        l_idx = BANDS.index(l_cefr)
        r_idx = BANDS.index(r_cefr)
        w_cefr = BANDS[min(l_idx, r_idx)]
        w_ielts = None
        w_lo, w_hi = cefr_to_ielts(w_cefr)
        w_num = (w_lo + w_hi) / 2.0

    # Speaking
    if speaking_band is not None:
        s_cefr = ielts_to_cefr(speaking_band)
        s_ielts = speaking_band
        s_num = speaking_band
    else:
        l_idx = BANDS.index(l_cefr)
        r_idx = BANDS.index(r_cefr)
        s_cefr = BANDS[min(l_idx, r_idx)]
        s_ielts = None
        s_lo, s_hi = cefr_to_ielts(s_cefr)
        s_num = (s_lo + s_hi) / 2.0

    ob = overall_band({
        "listening": l_num,
        "reading": r_num,
        "writing": w_num,
        "speaking": s_num,
    })

    # Compute approximate CEFR for each skill (with confidence/borderline)
    l_cefr_approx = ielts_to_cefr_approx(l_num)
    r_cefr_approx = ielts_to_cefr_approx(r_num)
    w_cefr_approx = ielts_to_cefr_approx(w_num) if writing_band is not None else None
    s_cefr_approx = ielts_to_cefr_approx(s_num) if speaking_band is not None else None
    overall_cefr_approx = ielts_to_cefr_approx(ob)

    per_skill: dict = {
        "listening": {
            "cefr": l_cefr,
            "cefrApprox": {
                "level": l_cefr_approx.level,
                "confidence": l_cefr_approx.confidence,
                "borderlineWith": l_cefr_approx.borderline_with,
                "ieltsRange": l_cefr_approx.ielts_range,
                "mappingSource": l_cefr_approx.mapping_source,
            },
            "ieltsApprox": l_num,
            "raw": l_raw,
            "confidence": l_conf,
        },
        "reading": {
            "cefr": r_cefr,
            "cefrApprox": {
                "level": r_cefr_approx.level,
                "confidence": r_cefr_approx.confidence,
                "borderlineWith": r_cefr_approx.borderline_with,
                "ieltsRange": r_cefr_approx.ielts_range,
                "mappingSource": r_cefr_approx.mapping_source,
            },
            "ieltsApprox": r_num,
            "raw": r_raw,
            "confidence": r_conf,
        },
        "writing": {
            "cefr": w_cefr,
            "ielts": w_ielts,
        },
        "speaking": {
            "cefr": s_cefr,
            "ielts": s_ielts,
        },
    }

    # Add assessed=False flag for skipped skills
    if writing_band is None:
        per_skill["writing"]["assessed"] = False
        per_skill["writing"]["confidence"] = "low"
        per_skill["writing"]["cefrApprox"] = {
            "level": w_cefr_approx.level if w_cefr_approx else "unassessed",
            "confidence": "low",
            "borderlineWith": None,
            "ieltsRange": [0, 0],
            "mappingSource": "estimated from L/R",
        }
    if speaking_band is None:
        per_skill["speaking"]["assessed"] = False
        per_skill["speaking"]["confidence"] = "low"
        per_skill["speaking"]["cefrApprox"] = {
            "level": s_cefr_approx.level if s_cefr_approx else "unassessed",
            "confidence": "low",
            "borderlineWith": None,
            "ieltsRange": [0, 0],
            "mappingSource": "estimated from L/R",
        }

    return {
        "perSkill": per_skill,
        "overallBand": ob,
        "cefr": ielts_to_cefr(ob),
        "cefrApprox": {
            "level": overall_cefr_approx.level,
            "confidence": overall_cefr_approx.confidence,
            "borderlineWith": overall_cefr_approx.borderline_with,
            "ieltsRange": overall_cefr_approx.ielts_range,
            "mappingSource": overall_cefr_approx.mapping_source,
        },
        "gapToTarget": round(target_band - ob, 2),
    }


# ---------------------------------------------------------------------------
# Combo serving (takes a repo — only non-pure function here)
# ---------------------------------------------------------------------------

_STRIP_KEYS = {"answer"}


def _strip_item_payload(item: dict) -> dict:
    """Return item dict with answer key removed from payload."""
    stripped_payload = {
        k: v for k, v in item.get("payload", {}).items()
        if k not in _STRIP_KEYS
    }
    return {
        "id": item.get("id"),
        "skill": item.get("skill"),
        "bandTag": item.get("bandTag"),
        "type": item.get("type"),
        "payload": stripped_payload,
    }


def serve_combo(repo) -> dict:
    """
    Pick a random combo from the repo, strip answer keys from item payloads,
    and return the client-safe dict.

    Shape returned:
    {
      "comboId": int,
      "targetMinutes": int,
      "sections": dict,
      "items": [...stripped items...]
    }
    """
    combo_ids = repo.list_combo_ids()
    chosen_id = random.choice(combo_ids)
    combo = repo.get_combo(chosen_id)

    return {
        "comboId": combo["comboId"],
        "targetMinutes": combo["targetMinutes"],
        "sections": combo["sections"],
        "items": [_strip_item_payload(it) for it in combo["items"]],
    }

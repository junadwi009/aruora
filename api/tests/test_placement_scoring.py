"""
Tests for domain/scoring.py and domain/placement.py.
Follow the spec in task-08-brief.md verbatim.
"""

from app.domain.scoring import locator_band, overall_band, ielts_round_half_band


# ── locator_band tests ────────────────────────────────────────────────────────

def test_locator_blueprint_example():
    # Reading: A2 2/2, B1 4/4, B2 3/4, C1 0/2, C2 0/1
    # A1A2 passes, B1 passes, B2 3/4=0.75 >= 0.667 passes, C1 0/2 fails -> B2
    tiers = {"A1A2": (2, 2), "B1": (4, 4), "B2": (3, 4), "C1": (0, 2), "C2": (0, 1)}
    assert locator_band(tiers) == "B2"


def test_locator_weak_user():
    tiers = {"A1A2": (2, 2), "B1": (1, 4), "B2": (0, 4), "C1": (0, 2), "C2": (0, 1)}
    assert locator_band(tiers) == "A1A2"


def test_locator_all_fail_floor():
    tiers = {"A1A2": (0, 2), "B1": (0, 4), "B2": (0, 4), "C1": (0, 2), "C2": (0, 1)}
    assert locator_band(tiers) == "A1A2"


# ── IELTS official half-band rounding regression tests ─────────────────────────
# WS02-01: official rounding with ties rounding UP (not banker's rounding)

def test_ielts_round_half_band_official_cases():
    # Official IELTS rounding cases
    assert ielts_round_half_band(6.25) == 6.5
    assert ielts_round_half_band(6.75) == 7.0
    assert ielts_round_half_band(6.125) == 6.0
    assert ielts_round_half_band(3.875) == 4.0

    # Already half/whole values remain unchanged
    assert ielts_round_half_band(6.0) == 6.0
    assert ielts_round_half_band(6.5) == 6.5
    assert ielts_round_half_band(7.0) == 7.0
    assert ielts_round_half_band(4.5) == 4.5


def test_overall_band_rounds_half():
    # Uses IELTS rounding internally
    assert overall_band({"l": 6.0, "r": 7.0, "w": 5.0, "s": 5.0}) == 6.0


def test_overall_band_ielts_rounding_edge_cases():
    # mean = 6.25 → overall 6.5
    assert overall_band({"l": 6.0, "r": 6.5, "w": 6.0, "s": 6.5}) == 6.5
    # mean = 6.75 → overall 7.0
    assert overall_band({"l": 7.0, "r": 6.5, "w": 7.0, "s": 6.5}) == 7.0
    # mean = 6.125 → overall 6.0
    assert overall_band({"l": 6.0, "r": 6.0, "w": 6.0, "s": 6.5}) == 6.0


# ── grade_placement tests ─────────────────────────────────────────────────────

def test_grade_placement_shape():
    from app.domain.placement import grade_placement

    # Minimal combo with 2 listening items + 2 reading items
    combo = {
        "comboId": 1,
        "targetMinutes": 50,
        "sections": {},
        "items": [
            {
                "id": 1,
                "skill": "listening",
                "bandTag": "B1",
                "type": "mcq",
                "payload": {"stem": "q1", "answer": "A"},
            },
            {
                "id": 2,
                "skill": "listening",
                "bandTag": "B2",
                "type": "mcq",
                "payload": {"stem": "q2", "answer": "B"},
            },
            {
                "id": 3,
                "skill": "reading",
                "bandTag": "B1",
                "type": "tfng",
                "payload": {"stem": "q3", "answer": "True"},
            },
            {
                "id": 4,
                "skill": "reading",
                "bandTag": "B2",
                "type": "tfng",
                "payload": {"stem": "q4", "answer": "False"},
            },
        ],
    }
    # Answer item 1 correctly (B1 listening correct), item 2 wrong (B2 wrong)
    # Answer item 3 correctly (B1 reading correct), item 4 wrong (B2 wrong)
    answers = {
        "1": "A",      # correct
        "2": "X",      # wrong
        "3": "True",   # correct
        "4": "X",      # wrong
    }

    result = grade_placement(
        combo=combo,
        answers=answers,
        writing_band=5.0,
        speaking_band=5.0,
        target_band=6.5,
    )

    assert "perSkill" in result
    ps = result["perSkill"]
    assert "listening" in ps
    assert "reading" in ps
    assert "writing" in ps
    assert "speaking" in ps

    assert "overallBand" in result
    # overallBand must be a multiple of 0.5
    ob = result["overallBand"]
    assert isinstance(ob, float)
    assert ob * 2 == round(ob * 2), f"overallBand {ob} is not a multiple of 0.5"

    assert "cefr" in result
    assert result["cefr"] in ("A1A2", "B1", "B2", "C1", "C2")

    assert "gapToTarget" in result
    assert result["gapToTarget"] == round(6.5 - result["overallBand"], 2)


# ── serve_combo strips answers ────────────────────────────────────────────────

def test_serve_combo_strips_answers():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.data.models import Base
    from app.data.repositories import Repository
    from app.data.seed import seed_all
    from app.domain.placement import serve_combo

    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    sf = sessionmaker(bind=eng)
    seed_all(sf)

    repo = Repository(sf)
    result = serve_combo(repo)

    assert "comboId" in result
    assert "targetMinutes" in result
    assert "sections" in result
    assert "items" in result

    for item in result["items"]:
        assert "answer" not in item.get("payload", {}), (
            f"answer key leaked in item payload: {item}"
        )

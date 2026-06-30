"""Phase 2d-1: pure lesson-planning helpers (focus pick + current day)."""
from datetime import date, datetime, timezone

from app.domain.lesson_plan import pick_focus, current_day


def test_pick_focus_lowest_band():
    levels = [("reading", "C1"), ("writing", "B1"), ("listening", "B2"), ("speaking", "B2")]
    assert pick_focus(levels) == "writing"


def test_pick_focus_tiebreak_by_plan_weight():
    # writing + listening both B1 → writing wins (highest plan priority)
    assert pick_focus([("listening", "B1"), ("writing", "B1")]) == "writing"
    # listening + speaking both B1 → listening wins
    assert pick_focus([("speaking", "B1"), ("listening", "B1")]) == "listening"


def test_pick_focus_default_when_empty():
    assert pick_focus([]) == "writing"


def test_current_day_within_range():
    start = datetime(2026, 6, 20, tzinfo=timezone.utc)
    # 10 days later → day 11
    assert current_day(start, 30, date(2026, 6, 30)) == 11
    # on start date → day 1
    assert current_day(start, 30, date(2026, 6, 20)) == 1


def test_current_day_clamped_to_length():
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert current_day(start, 30, date(2026, 8, 1)) == 30  # past the end → clamp


def test_current_day_no_program():
    assert current_day(None, None, date(2026, 6, 30)) == 1

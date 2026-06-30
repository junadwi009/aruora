"""Phase 2d-4: SM-2 scheduling (pure)."""
from app.domain.sm2 import schedule


def test_good_progression():
    # first good review (q=4): reps 0→1, interval→1
    s = schedule(ease=2.5, interval=0, reps=0, lapses=0, quality=4)
    assert s["reps"] == 1 and s["interval"] == 1
    # second good: reps 1→2, interval→6
    s = schedule(ease=s["ease"], interval=s["interval"], reps=s["reps"], lapses=0, quality=4)
    assert s["reps"] == 2 and s["interval"] == 6
    # third good: interval = round(6 * ease)
    s3 = schedule(ease=s["ease"], interval=s["interval"], reps=s["reps"], lapses=0, quality=4)
    assert s3["interval"] == round(6 * s["ease"])


def test_again_resets_and_counts_lapse():
    s = schedule(ease=2.5, interval=20, reps=5, lapses=0, quality=1)
    assert s["reps"] == 0
    assert s["interval"] == 1
    assert s["lapses"] == 1


def test_ease_floor():
    # repeated low-but-passing quality drives ease down but never below 1.3
    ease = 2.5
    for _ in range(20):
        ease = schedule(ease=ease, interval=1, reps=1, lapses=0, quality=3)["ease"]
    assert ease >= 1.3

"""
Phase 2d-1 — guided lessons (Teach → Practice → Produce → Review).

- GET  /api/lesson/today                         → today's day/focus + cached lesson (or null)
- POST /api/lesson/generate {day?,focus?,band?,force?} → generate + cache, return lesson
- GET  /api/lesson/<int:day>                      → cached lesson for a day (or null)
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.domain.lesson_plan import current_day, pick_focus
from app.routes._deps import _gateway, _repo

bp = Blueprint("lesson", __name__)

_DEFAULT_BAND = "B1"


def _today_plan():
    """Compute (day, focus, skill, band) for today from skill_levels + program."""
    repo = _repo()
    user = repo.get_user()
    levels = repo.get_skill_levels(user.id) if user else []
    focus = pick_focus(levels)
    band = dict(levels).get(focus, _DEFAULT_BAND)
    program = repo.get_latest_program(user.id) if user else None
    today = datetime.now(timezone.utc).date()
    day = current_day(
        getattr(program, "start_date", None),
        getattr(program, "length_days", None),
        today,
    )
    return day, focus, band


@bp.get("/api/lesson/today")
def lesson_today():
    day, focus, band = _today_plan()
    cached = _repo().get_lesson(day)
    return jsonify({
        "day": day,
        "focus": focus,
        "skill": focus,
        "band": band,
        "lesson": cached["lesson"] if cached else None,
    }), 200


@bp.post("/api/lesson/generate")
def lesson_generate():
    body = request.get_json(force=True) or {}
    repo = _repo()

    t_day, t_focus, t_band = _today_plan()
    day = int(body.get("day") or t_day)
    focus = body.get("focus") or t_focus
    band = body.get("band") or t_band
    force = bool(body.get("force"))

    cached = repo.get_lesson(day)
    if cached and not force:
        return jsonify({"day": day, "focus": cached["focus"], "skill": focus,
                        "band": band, "lesson": cached["lesson"]}), 200

    lesson = _gateway().generate("lesson", skill=focus, band=band, day=day, focus=focus, tasks=focus)
    repo.save_lesson(day, lesson, focus)
    return jsonify({"day": day, "focus": focus, "skill": focus, "band": band, "lesson": lesson}), 200


@bp.get("/api/lesson/<int:day>")
def lesson_by_day(day):
    cached = _repo().get_lesson(day)
    if cached is None:
        return jsonify({"day": day, "lesson": None}), 200
    return jsonify({"day": day, "focus": cached["focus"], "lesson": cached["lesson"]}), 200

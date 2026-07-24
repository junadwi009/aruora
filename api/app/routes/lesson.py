"""
Phase 2d-1 — guided lessons (Teach → Practice → Produce → Review).

- GET  /api/lesson/today                         → today's day/focus + cached lesson (or null)
- POST /api/lesson/generate {day?,focus?,band?,force?} → generate + cache, return lesson
- GET  /api/lesson/<int:day>                      → cached lesson for a day (or null)
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.domain.lesson_plan import current_day, pick_focus
from app.errors import ApiError
from app.routes._deps import _cfg, _gateway, _lang, _repo, _uid, _require_uid
from app.routes._gencap import cap_reached, note_generation

bp = Blueprint("lesson", __name__)

_DEFAULT_BAND = "B1"


def _today_plan(uid):
    """Compute (day, focus, skill, band) for today from this user's levels + program."""
    repo = _repo()
    levels = repo.get_skill_levels(uid) if uid else []
    focus = pick_focus(levels)
    band = dict(levels).get(focus, _DEFAULT_BAND)
    program = repo.get_latest_program(uid) if uid else None
    today = datetime.now(timezone.utc).date()
    day = current_day(
        getattr(program, "start_date", None),
        getattr(program, "length_days", None),
        today,
    )
    return day, focus, band


@bp.get("/api/lesson/today")
def lesson_today():
    uid = _uid()
    day, focus, band = _today_plan(uid)
    cached = _repo().get_lesson(uid, day) if uid is not None else None
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
    uid = _require_uid()

    t_day, t_focus, t_band = _today_plan(uid)
    day = int(body.get("day") or t_day)
    focus = body.get("focus") or t_focus
    band = body.get("band") or t_band
    force = bool(body.get("force"))

    cached = repo.get_lesson(uid, day)
    if cached and not force:
        return jsonify({"day": day, "focus": cached["focus"], "skill": focus,
                        "band": band, "lesson": cached["lesson"]}), 200

    if cap_reached(uid, repo, _cfg()):
        raise ApiError("GEN_CAP_REACHED", "Daily generation limit reached", 429)
    lesson = _gateway().generate("lesson", skill=focus, band=band, lang=_lang(), day=day, focus=focus, tasks=focus)
    note_generation(uid, repo)
    repo.save_lesson(uid, day, lesson, focus)
    return jsonify({"day": day, "focus": focus, "skill": focus, "band": band, "lesson": lesson}), 200


@bp.get("/api/lesson/<int:day>")
def lesson_by_day(day):
    uid = _uid()
    cached = _repo().get_lesson(uid, day) if uid is not None else None
    if cached is None:
        return jsonify({"day": day, "lesson": None}), 200
    return jsonify({"day": day, "focus": cached["focus"], "lesson": cached["lesson"]}), 200

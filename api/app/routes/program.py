"""
POST /api/program            — create program + milestones for active user.
GET  /api/program/milestones — list milestones for the user's latest program.
"""
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.errors import ApiError
from app.schemas import ProgramIn, ProgramOut, MilestoneOut
from app.domain.program import build_milestones
from app.routes._deps import _repo, _uid, _require_uid

bp = Blueprint("program", __name__)

_SKILLS = ("listening", "reading", "writing", "speaking")


@bp.post("/api/program")
def program_create():
    try:
        data = ProgramIn(**request.get_json(force=True))
    except ValidationError as e:
        raise ApiError("VALIDATION", "Invalid request", 422, e.errors())

    repo = _repo()
    user = repo.get_user_by_id(_require_uid())
    if user is None:
        raise ApiError("NOT_FOUND", "no user profile", 404)

    # Build start_levels dict; default missing skills to "B1"
    raw_levels = repo.get_skill_levels(user.id)
    start_levels: dict[str, str] = {skill: "B1" for skill in _SKILLS}
    for skill, band in raw_levels:
        start_levels[skill] = band

    ms = build_milestones(data.length_days, start_levels, user.target_band)

    prog = repo.create_program(user.id, data.length_days)
    repo.add_milestones(prog.id, ms)

    return jsonify(
        ProgramOut(
            program={"id": prog.id, "lengthDays": prog.length_days, "status": prog.status},
            milestones=[MilestoneOut(**m) for m in ms],
        ).model_dump(by_alias=True)
    ), 200


@bp.get("/api/program/milestones")
def program_milestones():
    uid = _uid()
    if uid is None:
        return jsonify([]), 200
    repo = _repo()
    prog = repo.get_latest_program(uid)
    if prog is None:
        return jsonify([]), 200

    return jsonify(repo.get_milestones(prog.id)), 200


@bp.post("/api/program/milestones")
def milestone_add():
    b = request.get_json(force=True) or {}
    mid = _repo().add_milestone(
        _require_uid(), b.get("title", "Milestone"),
        int(b.get("dayTarget", 30)), b.get("targets", {}),
    )
    if mid is None:
        raise ApiError("NOT_FOUND", "No active program — choose a program first", 404)
    return jsonify({"id": mid}), 200


@bp.put("/api/program/milestones/<int:milestone_id>")
def milestone_update(milestone_id):
    b = request.get_json(force=True) or {}
    out = _repo().update_milestone(_require_uid(), milestone_id, b)
    if out is None:
        raise ApiError("NOT_FOUND", "Milestone not found", 404)
    return jsonify(out), 200


@bp.delete("/api/program/milestones/<int:milestone_id>")
def milestone_delete(milestone_id):
    if not _repo().delete_milestone(_require_uid(), milestone_id):
        raise ApiError("NOT_FOUND", "Milestone not found", 404)
    return jsonify({"deleted": milestone_id}), 200

"""
GET /api/skill-levels — return current CEFR band per skill for the active user.
"""
from flask import Blueprint, jsonify

from app.schemas import SkillLevelOut
from app.routes._deps import _repo, _uid

bp = Blueprint("skills", __name__)


@bp.get("/api/skill-levels")
def skill_levels():
    uid = _uid()
    if uid is None:
        return jsonify([]), 200

    levels = _repo().get_skill_levels(uid)
    return jsonify([SkillLevelOut(skill=s, band=b).model_dump(by_alias=True) for s, b in levels]), 200

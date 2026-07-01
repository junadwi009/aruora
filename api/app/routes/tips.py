"""
GET /api/tips/<skill> — return fixture tips for a given skill (no LLM).
"""
from flask import Blueprint, jsonify

from app.errors import ApiError
from app.data.seed import load_fixture
from app.routes._deps import _lang

bp = Blueprint("tips", __name__)


@bp.get("/api/tips/<skill>")
def tips(skill: str):
    # Tips are coaching guidance (not exam content), so they localize: serve the
    # Indonesian fixture when the UI language is Indonesian, English otherwise.
    fixture = "tips_id" if _lang() == "id" else "tips"
    all_tips = load_fixture(fixture)
    if skill not in all_tips:
        raise ApiError("NOT_FOUND", f"no tips for {skill}", 404)
    return jsonify(all_tips[skill]), 200

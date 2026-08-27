"""
POST /api/onboarding — create a user profile.
"""
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.errors import ApiError
from app.schemas import OnboardingIn, OnboardingOut
from app.routes._deps import _repo
from app.session import login_session

bp = Blueprint("onboarding", __name__)


@bp.post("/api/onboarding")
def onboarding():
    try:
        data = OnboardingIn(**request.get_json(force=True))
    except ValidationError as e:
        raise ApiError("VALIDATION", "Invalid request", 422, e.errors())

    repo = _repo()
    # Normalise a month-only deadline (YYYY-MM) to the first of that month so
    # the stored exam_date is always a full ISO date (YYYY-MM-DD).
    exam_date = data.exam_date
    if exam_date and len(exam_date) == 7:
        exam_date = f"{exam_date}-01"
    user = repo.create_user(
        name=data.name,
        goal=data.goal,
        target_band=data.target_band,
        skill_targets=data.skill_targets,
        exam_date=exam_date,
    )
    # Establish the session so all subsequent data is scoped to this profile
    # (anonymous until they register an email/password in 3c).
    login_session(user.id)

    # WS21 — server-authoritative funnel events (after the action succeeded).
    from app.routes._analytics import capture_acquisition, emit
    capture_acquisition(user.id)
    emit("goal_selected", user_id=user.id, goal=data.goal)
    emit("target_band_selected", user_id=user.id, target_band=data.target_band)
    if exam_date:
        emit("deadline_added", user_id=user.id, deadline_month=exam_date[:7])
    emit("onboarding_completed", user_id=user.id)

    return jsonify(
        OnboardingOut(
            id=user.id,
            name=user.name,
            goal=user.goal,
            targetBand=user.target_band,
            skillTargets=user.skill_targets,
        ).model_dump(by_alias=True)
    ), 200

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
    user = repo.create_user(
        name=data.name,
        goal=data.goal,
        target_band=data.target_band,
        skill_targets=data.skill_targets,
    )
    # Establish the session so all subsequent data is scoped to this profile
    # (anonymous until they register an email/password in 3c).
    login_session(user.id)

    return jsonify(
        OnboardingOut(
            id=user.id,
            name=user.name,
            goal=user.goal,
            targetBand=user.target_band,
            skillTargets=user.skill_targets,
        ).model_dump(by_alias=True)
    ), 200

"""Create an anonymous profile, or complete the current profile without identity loss.

The authenticated route always derives ownership from the server session. It
never accepts a user id from the payload and never creates a replacement account.
"""
from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from app.errors import ApiError
from app.schemas import OnboardingIn, OnboardingOut
from app.routes._deps import _repo
from app.session import current_uid, login_session

bp = Blueprint("onboarding", __name__)


@bp.post("/api/onboarding")
def onboarding():
    try:
        data = OnboardingIn(**request.get_json(force=True))
    except ValidationError as exc:
        raise ApiError("VALIDATION", "Invalid request", 422, exc.errors())
    repo = _repo()
    exam_date = data.exam_date
    if exam_date and len(exam_date) == 7:
        exam_date = f"{exam_date}-01"
    uid = current_uid()
    if uid is not None:
        # New landing -> register/login -> app -> setup MUST retain identity.
        # Preserve credentials, verification state, sessions, attempts and targets
        # that were not supplied in this validated request.
        user = repo.complete_onboarding(
            uid, name=data.name, goal=data.goal, target_band=data.target_band,
            skill_targets=(data.skill_targets if "skill_targets" in data.model_fields_set else None),
            exam_date=exam_date,
        )
        if user is None:
            raise ApiError("UNAUTHORIZED", "Profile no longer available", 401)
    else:
        # Backward-compatible anonymous pilot path. The new public UI does not
        # offer this path, but removing it is outside this UI patch's scope.
        user = repo.create_user(
            name=data.name, goal=data.goal, target_band=data.target_band,
            skill_targets=data.skill_targets, exam_date=exam_date,
        )
        login_session(user.id)

    from app.routes._analytics import capture_acquisition, emit
    capture_acquisition(user.id)
    emit("goal_selected", user_id=user.id, goal=data.goal)
    emit("target_band_selected", user_id=user.id, target_band=data.target_band)
    if exam_date:
        emit("deadline_added", user_id=user.id, deadline_month=exam_date[:7])
    emit("onboarding_completed", user_id=user.id)
    return jsonify(OnboardingOut(
        id=user.id, name=user.name, goal=user.goal,
        targetBand=user.target_band, skillTargets=user.skill_targets,
    ).model_dump(by_alias=True)), 200

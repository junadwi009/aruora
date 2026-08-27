"""
POST /api/placement/start  — serve a placement combo (no answer keys).
POST /api/placement/submit — grade answers, seed skill levels, save attempt.
"""
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.errors import ApiError
from app.schemas import PlacementStartOut, PlacementSubmitIn, PlacementResultOut
from app.domain.placement import serve_combo, grade_placement
from app.routes._deps import _repo, _gateway, _require_uid

bp = Blueprint("placement", __name__)


@bp.post("/api/placement/start")
def placement_start():
    repo = _repo()
    out = serve_combo(repo)
    # WS21 — funnel event (authenticated context when present).
    try:
        from app.routes._analytics import emit
        emit("placement_started")
    except Exception:  # noqa: BLE001 — analytics is fail-open
        pass
    return jsonify(
        PlacementStartOut(
            comboId=out["comboId"],
            sections=out["sections"],
            targetMinutes=out["targetMinutes"],
            items=out["items"],
        ).model_dump(by_alias=True)
    ), 200


@bp.post("/api/placement/submit")
def placement_submit():
    try:
        data = PlacementSubmitIn(**request.get_json(force=True))
    except ValidationError as e:
        raise ApiError("VALIDATION", "Invalid request", 422, e.errors())

    repo = _repo()
    gateway = _gateway()

    # 1. Require the session user profile
    user = repo.get_user_by_id(_require_uid())
    if user is None:
        raise ApiError("NOT_FOUND", "no user profile", 404)
    target = user.target_band

    # 2. Fetch combo WITH answer keys (for grading)
    combo = repo.get_combo(data.combo_id)

    # 3. Score writing/speaking via gateway if samples provided
    writing_band = None
    if data.writing_samples:
        g = gateway.score("writing", **data.writing_samples)
        writing_band = g["bands"]["overall"]

    speaking_band = None
    if data.speaking_text:
        g = gateway.score("speaking", transcript=data.speaking_text)
        speaking_band = g["bands"]["overall"]

    # 4. Grade placement
    result = grade_placement(combo, data.answers, writing_band, speaking_band, target)

    # 5. Seed skill levels
    for skill, info in result["perSkill"].items():
        repo.set_skill_level(user.id, skill, info["cefr"])

    # 6. Persist attempt
    repo.save_placement_attempt(
        user_id=user.id,
        combo_id=data.combo_id,
        duration_sec=data.duration_sec,
        per_skill=result["perSkill"],
        overall_band=result["overallBand"],
        cefr=result["cefr"],
        gap_to_target=result["gapToTarget"],
    )

    # 7. Validate and return result through PlacementResultOut (wire JSON unchanged)
    # WS21 — funnel completion events, server-authoritative.
    from app.routes._analytics import emit
    emit("placement_completed", user_id=user.id,
         writing_assessed=writing_band is not None,
         speaking_assessed=speaking_band is not None)
    emit("result_viewed", user_id=user.id)
    return jsonify(PlacementResultOut.model_validate(result).model_dump(by_alias=True)), 200

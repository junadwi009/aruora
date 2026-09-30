"""v1.2 practice session + answer submission; browser scores are rejected."""
from flask import Blueprint, jsonify, request
from app.errors import ApiError
from app.routes._deps import _repo, _require_uid, _cfg, _jobs
from app.services import practice_integrity as integrity
from app.services.task_pool import serve_next

bp = Blueprint("practice", __name__)


def start_for(skill, band):
    uid = _require_uid()
    repo, cfg = _repo(), _cfg()
    if skill not in integrity.SKILLS or band not in integrity.LEVELS:
        raise ApiError("VALIDATION", "Unsupported practice skill or level", 422)
    served = serve_next(skill, band, uid, repo, cfg)
    if served is None:
        # Replenishment remains system-budgeted/idempotent. No paid work inline.
        jobs = _jobs()
        if jobs is not None and getattr(jobs, "mode", "inline") == "queued":
            from app.routes._gencap import today_utc
            try:
                jobs.enqueue("replenish_pool", queue="llm_generate",
                             payload={"skill": skill, "band": band},
                             idempotency_key=f"{skill}:{band}:{today_utc()}")
            except ApiError:
                pass
        raise ApiError("POOL_EMPTY", "Practice content is being prepared; try again later", 503)
    return integrity.start(repo.session_factory, uid, skill, served["servedFrom"]["band"],
                           served["payload"], repeat=served["repeat"])


@bp.post("/api/practice/start")
def practice_start():
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not set(body) <= {"skill", "band"}:
        raise ApiError("VALIDATION", "Invalid practice request", 422)
    skill = body.get("skill")
    return jsonify(start_for(skill, body.get("band") or "B1")), 200


@bp.post("/api/practice/attempt")
def practice_attempt():
    uid = _require_uid()
    result, created = integrity.submit(_repo().session_factory, uid, request.get_json(silent=True))
    if created:
        from app.routes._analytics import emit
        emit("practice_completed", user_id=uid, skill=result["skill"],
             correct=result["correct"], total=result["total"])
    return jsonify(result), 200


@bp.delete("/api/practice/session/<pid>")
def practice_close(pid):
    integrity.close(_repo().session_factory, _require_uid(), pid)
    return jsonify({"ok": True}), 200


@bp.get("/api/practice/set")
def practice_set():
    raise ApiError("PRACTICE_API_CHANGED", "Use POST /api/practice/start", 410)


@bp.post("/api/practice/generate")
def practice_generate():
    # Placement transition is not a generation job; no fabricated job progress.
    raise ApiError("PRACTICE_API_CHANGED", "Use POST /api/practice/start", 410)


@bp.get("/api/practice/status")
def practice_status():
    raise ApiError("PRACTICE_API_CHANGED", "No generation job was created", 410)

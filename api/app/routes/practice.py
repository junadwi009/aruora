"""
POST /api/practice/generate  — stub job submission (synchronous, seed sets).
GET  /api/practice/status    — always done=True, progress=100 (stub).
GET  /api/practice/set       — serve a generated set by skill + optional band.
"""
from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.schemas import GenerateJobOut, JobStatusOut
from app.routes._deps import _repo

bp = Blueprint("practice", __name__)


@bp.post("/api/practice/generate")
def practice_generate():
    return jsonify(GenerateJobOut(jobId="stub-1").model_dump(by_alias=True)), 200


@bp.get("/api/practice/status")
def practice_status():
    return jsonify(JobStatusOut(done=True, progress=100).model_dump(by_alias=True)), 200


@bp.post("/api/practice/attempt")
def practice_attempt():
    """Persist a Reading/Listening practice score so it shows in Progress trends."""
    b = request.get_json(force=True) or {}
    skill = b.get("skill")
    if skill not in ("reading", "listening"):
        raise ApiError("VALIDATION", "skill must be reading or listening", 422)
    correct, total = int(b.get("correct", 0)), int(b.get("total", 0))
    band = float(b.get("band", 0.0))
    saved_id = _repo().save_attempt(
        type=skill,
        task=f"{correct}/{total}",
        prompt=b.get("title", ""),
        body="",
        bands={"overall": band},
        criteria={},
        cefr="",
        metrics={"correct": correct, "total": total},
    )
    return jsonify({"savedId": saved_id}), 200


@bp.get("/api/practice/set")
def practice_set():
    skill = request.args.get("skill")
    band = request.args.get("band")

    if not skill:
        raise ApiError("VALIDATION", "skill query param required", 400)

    repo = _repo()

    payload = None
    if band:
        payload = repo.serve_set(skill, band)

    if payload is None:
        payload = repo.serve_any_set(skill)

    if payload is None:
        raise ApiError("NOT_FOUND", f"no set for {skill}", 404)

    # free-form generated set payload; shape validated client-side
    return jsonify(payload), 200

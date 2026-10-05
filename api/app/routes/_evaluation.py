"""Versioned queue receipt on production scoring endpoints; no heavy work here."""
import re
from flask import current_app, jsonify, request
from app.errors import ApiError
from app.routes._deps import _cfg, _jobs, _lang, _repo
from app.costguard import ensure_ai_available


def maybe_enqueue(kind, body, uid):
    jobs = _jobs()
    key = request.headers.get("Idempotency-Key", "")
    if (jobs is None or jobs.mode != "queued") and not key:
        return None  # Legacy inline development clients retain their 200 contract.
    if jobs is None:
        raise ApiError("UNAVAILABLE", "Evaluation jobs are unavailable", 503)
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", key):
        raise ApiError("IDEMPOTENCY_REQUIRED", "Provide an Idempotency-Key of 8-64 letters, digits, underscores or hyphens", 422)
    ensure_ai_available(_cfg(), _repo())
    job, _ = jobs.enqueue(f"score_{kind}", queue="llm_score", user_id=uid,
        payload={"input": body.model_dump(by_alias=True), "lang": _lang()}, idempotency_key=key)
    return jsonify({"jobId": job["id"], "queued": True, "status": job["status"]}), 202, {"Retry-After": "2"}


def evaluation_context():
    return {"repo": _repo(), "cfg": _cfg(), "gateway": current_app.config["GATEWAY"],
            "jobs": _jobs(), "concurrency": current_app.config.get("CONCURRENCY")}

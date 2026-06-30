"""Phase 2d-2 — mock-test score persistence (Listening + Reading)."""
from flask import Blueprint, jsonify, request

from app.routes._deps import _repo, _uid, _require_uid

bp = Blueprint("mocks", __name__)


@bp.post("/api/mocks")
def save_mock():
    b = request.get_json(force=True) or {}
    mid = _repo().save_mock(
        _require_uid(),
        float(b.get("listening", 0.0)),
        float(b.get("reading", 0.0)),
        float(b.get("overall", 0.0)),
    )
    return jsonify({"id": mid}), 200


@bp.get("/api/mocks")
def list_mocks():
    uid = _uid()
    return jsonify(_repo().list_mocks(uid) if uid is not None else []), 200

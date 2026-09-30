"""Phase 2d-2 — mock-test score persistence (Listening + Reading)."""
from flask import Blueprint, jsonify

from app.routes._deps import _repo, _uid, _require_uid
from app.schemas import MockSaveIn
from app.validation import parse_body

bp = Blueprint("mocks", __name__)


@bp.post("/api/mocks")
def save_mock():
    from app.errors import ApiError
    _require_uid()
    raise ApiError("MOCK_API_CHANGED", "Client-provided mock bands are not accepted. Submit each practice session to /api/practice/attempt.", 410)


@bp.get("/api/mocks")
def list_mocks():
    uid = _uid()
    return jsonify(_repo().list_mocks(uid) if uid is not None else []), 200

"""Phase 2d-2 — mock-test score persistence (Listening + Reading)."""
from flask import Blueprint, jsonify

from app.routes._deps import _repo, _uid, _require_uid
from app.schemas import MockSaveIn
from app.validation import parse_body

bp = Blueprint("mocks", __name__)


@bp.post("/api/mocks")
def save_mock():
    b = parse_body(MockSaveIn)
    mid = _repo().save_mock(
        _require_uid(),
        float(b.listening),
        float(b.reading),
        float(b.overall),
    )
    # WS21 — WML qualifying event after persistence.
    from app.routes._analytics import emit
    emit("mock_completed")
    return jsonify({"id": mid}), 200


@bp.get("/api/mocks")
def list_mocks():
    uid = _uid()
    return jsonify(_repo().list_mocks(uid) if uid is not None else []), 200

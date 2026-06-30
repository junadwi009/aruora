"""Phase 2d-4 — flashcard CRUD + SM-2 review."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _repo

bp = Blueprint("cards", __name__)


@bp.get("/api/cards")
def list_cards():
    repo = _repo()
    return jsonify({"cards": repo.list_cards(), "stats": repo.card_stats()}), 200


@bp.get("/api/cards/due")
def due_cards():
    return jsonify(_repo().due_cards(datetime.now(timezone.utc))), 200


@bp.post("/api/cards")
def add_cards():
    b = request.get_json(force=True) or {}
    repo = _repo()
    if isinstance(b.get("cards"), list):
        return jsonify({"added": repo.add_cards(b["cards"])}), 200
    front, back = b.get("front", ""), b.get("back", "")
    if not front or not back:
        raise ApiError("VALIDATION", "front and back are required", 422)
    return jsonify({"id": repo.add_card(front, back)}), 200


@bp.post("/api/cards/<int:card_id>/review")
def review_card(card_id):
    b = request.get_json(force=True) or {}
    out = _repo().review_card(card_id, int(b.get("quality", 0)), datetime.now(timezone.utc))
    if out is None:
        raise ApiError("NOT_FOUND", "Card not found", 404)
    return jsonify(out), 200


@bp.delete("/api/cards/<int:card_id>")
def delete_card(card_id):
    if not _repo().delete_card(card_id):
        raise ApiError("NOT_FOUND", "Card not found", 404)
    return jsonify({"deleted": card_id}), 200

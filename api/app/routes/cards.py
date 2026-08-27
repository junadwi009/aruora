"""Phase 2d-4 — flashcard CRUD + SM-2 review."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify

from app.errors import ApiError
from app.routes._deps import _repo, _uid, _require_uid
from app.schemas import CardAddIn, CardReviewIn
from app.validation import parse_body

bp = Blueprint("cards", __name__)


@bp.get("/api/cards")
def list_cards():
    uid = _uid()
    if uid is None:
        return jsonify({"cards": [], "stats": {"total": 0, "due": 0}}), 200
    repo = _repo()
    return jsonify({"cards": repo.list_cards(uid), "stats": repo.card_stats(uid)}), 200


@bp.get("/api/cards/due")
def due_cards():
    uid = _uid()
    if uid is None:
        return jsonify([]), 200
    return jsonify(_repo().due_cards(uid, datetime.now(timezone.utc))), 200


@bp.post("/api/cards")
def add_cards():
    b = parse_body(CardAddIn)
    repo = _repo()
    uid = _require_uid()
    if b.cards is not None:
        return jsonify({"added": repo.add_cards(
            uid, [{"front": c.front, "back": c.back} for c in b.cards])}), 200
    if not b.front or not b.back:
        raise ApiError("VALIDATION", "front and back are required", 422)
    return jsonify({"id": repo.add_card(uid, b.front, b.back)}), 200


@bp.post("/api/cards/<int:card_id>/review")
def review_card(card_id):
    b = parse_body(CardReviewIn)
    out = _repo().review_card(_require_uid(), card_id, b.quality, datetime.now(timezone.utc))
    if out is None:
        raise ApiError("NOT_FOUND", "Card not found", 404)
    return jsonify(out), 200


@bp.delete("/api/cards/<int:card_id>")
def delete_card(card_id):
    if not _repo().delete_card(_require_uid(), card_id):
        raise ApiError("NOT_FOUND", "Card not found", 404)
    return jsonify({"deleted": card_id}), 200

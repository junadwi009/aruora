"""Writing scoring: queued in production, shared evaluator for local development."""
from flask import Blueprint, jsonify
from app.routes._deps import _cfg, _lang, _require_uid
from app.routes._evaluation import maybe_enqueue, evaluation_context
from app.schemas import WritingEvaluateIn
from app.services.essay_metrics import compute_metrics
from app.services.evaluation import evaluate, validate_size
from app.validation import parse_body
bp = Blueprint("writing", __name__)


@bp.post("/api/writing/evaluate")
def writing_evaluate():
    uid = _require_uid()
    body = parse_body(WritingEvaluateIn)
    validate_size("writing", body, _cfg())
    receipt = maybe_enqueue("writing", body, uid)
    if receipt is not None:
        return receipt
    return jsonify(evaluate("writing", body, evaluation_context(), uid,
                            lang=_lang(), metrics_fn=compute_metrics)), 200

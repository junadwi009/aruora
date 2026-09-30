"""
Phase 2d-3 — pronunciation read-aloud drill.

- POST /api/pronounce/sentence {level?,topic?} → a read-aloud target {text,focus,tips[]}
- POST /api/pronounce/feedback {target,transcript,accuracy,missed[]} → {summary,wordTips[],prosody[]}

Scoring is approximate (browser recogniser word-match + LLM tips), not phoneme-level.
"""
from flask import Blueprint, jsonify

from app.errors import ApiError
from app.routes._deps import _cfg, _gateway, _lang, _repo, _require_uid
from app.routes._gencap import GEN_CAP_CODE
from app.schemas import PronounceFeedbackIn, PronounceSentenceIn
from app.services.ai_usage import note_custom_generation, require_custom_generation
from app.validation import parse_body

bp = Blueprint("pronounce", __name__)


@bp.post("/api/pronounce/sentence")
def pronounce_sentence():
    uid = _require_uid()  # authenticated only — this calls the paid LLM
    b = parse_body(PronounceSentenceIn)
    topic = b.topic or ""
    if len(topic) > _cfg().MAX_TOPIC_CHARS:
        raise ApiError("VALIDATION",
                       f"Topic is too long (max {_cfg().MAX_TOPIC_CHARS} characters)", 422)
    require_custom_generation(uid, _repo(), _cfg())
    out = _gateway().generate("generate", skill="pronounce", band=b.level or "B1",
                              topic=topic or None)
    note_custom_generation(uid, _repo())
    return jsonify(out), 200


@bp.post("/api/pronounce/feedback")
def pronounce_feedback():
    from flask import request
    from app.security.input_contracts import read_aloud_fields, word_evidence
    from app.costguard import ensure_ai_available, record_llm_usage
    uid = _require_uid()
    target, transcript = read_aloud_fields(request.get_json(silent=True))
    evidence = word_evidence(target, transcript)
    ensure_ai_available(_cfg(), _repo())
    try:
        out = _gateway().score("pronounce", lang=_lang(), target=target,
            transcript=transcript, accuracy=evidence["accuracy"],
            missed=", ".join(evidence["missed"])[:400] or "none")
    except ApiError as error:
        record_llm_usage(_repo(), cost_center="learner_scoring", op="score",
            meta=None, user_id=uid, skill="speaking", status="failed", error_code=error.code)
        raise
    record_llm_usage(_repo(), cost_center="learner_scoring", op="score",
        meta=out.pop("_meta_llm", None), user_id=uid, skill="speaking")
    out["assessmentScope"] = "text_word_matching_only"
    out["wordEvidence"] = evidence
    return jsonify(out), 200

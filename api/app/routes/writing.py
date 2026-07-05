"""
POST /api/writing/evaluate — score a writing attempt via the gateway.
"""
from flask import Blueprint, jsonify, request

from app.routes._deps import _gateway, _lang, _repo, _require_uid
from app.services.essay_metrics import compute_metrics

bp = Blueprint("writing", __name__)


@bp.post("/api/writing/evaluate")
def writing_evaluate():
    uid = _require_uid()  # gate BEFORE any paid LLM / spaCy metric work
    body = request.get_json(force=True) or {}
    essay = body.get("essay", "")

    # Compute deterministic metrics before calling the LLM
    metrics = compute_metrics(essay)

    # Build a short summary string for the examiner prompt
    mtld_val = metrics["lexicalDiversity"].get("mtld")
    mtld_str = f"{mtld_val:.1f}" if mtld_val is not None else "N/A"
    mean_sent = (
        metrics["syntax"].get("meanSentenceLength")
        if metrics.get("syntax")
        else None
    )
    mean_sent_str = f"{mean_sent:.1f}" if mean_sent is not None else "N/A"
    metrics_summary = (
        f"words={metrics['wordCount']}, "
        f"FleschKincaidGrade={metrics['readability']['fleschKincaidGrade']}, "
        f"MTLD={mtld_str}, "
        f"meanSentenceLength={mean_sent_str}"
    )

    gateway = _gateway()
    out = gateway.score(
        "writing",
        lang=_lang(),
        taskType=body.get("taskType"),
        prompt=body.get("prompt"),
        essay=essay,
        metricsSummary=metrics_summary,
    )

    # Attach metrics to the response (works in both stub and live mode)
    out["metrics"] = metrics

    # Persist the attempt for the Progress tab (history + trends).
    out["savedId"] = _repo().save_attempt(
        uid,
        type="writing",
        task=body.get("taskType", ""),
        prompt=body.get("prompt", ""),
        body=essay,
        bands=out.get("bands", {}),
        cefr=out.get("cefr", ""),
        metrics=out.get("metrics", {}),
        criteria={
            k: v for k, v in out.items()
            if k not in ("bands", "cefr", "metrics", "stub", "savedId")
        },
    )

    # gateway-defined shape; passthrough dict — shape validated client-side
    return jsonify(out), 200

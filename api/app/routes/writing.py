"""
POST /api/writing/evaluate — score a writing attempt via the gateway.

WS07: this is a paid, heavy surface — it passes the AI budget kill-switch /
provider-budget gate (WS07-08), is bounded by a per-user concurrency limit
(WS07-02), and records an append-only usage-ledger row for the call
(WS07-08). A budget halt never affects account/export/delete endpoints.
"""
from flask import Blueprint, jsonify

from app.costguard import ensure_ai_available, record_llm_usage
from app.errors import ApiError
from app.routes._deps import _cfg, _concurrency, _gateway, _lang, _repo, _require_uid
from app.schemas import WritingEvaluateIn
from app.services.essay_metrics import compute_metrics
from app.validation import parse_body

bp = Blueprint("writing", __name__)


@bp.post("/api/writing/evaluate")
def writing_evaluate():
    uid = _require_uid()  # gate BEFORE any paid LLM / spaCy metric work
    cfg = _cfg()
    repo = _repo()

    # WS07-08: provider budget / emergency kill-switch (fail closed, retryable).
    ensure_ai_available(cfg, repo)

    body = parse_body(WritingEvaluateIn)
    essay = body.essay

    # WS05-05: per-task untrusted-input ceiling (fail early, cheaply, clearly).
    max_essay = cfg.MAX_ESSAY_CHARS
    if len(essay) > max_essay:
        raise ApiError("VALIDATION",
                       f"Essay is too long (max {max_essay} characters)", 422)

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
    out = None
    llm_meta = None
    try:
        # WS07-02: bound the user's ACTIVE heavy evaluations (crash-safe TTL).
        conc = _concurrency()
        ttl = int(getattr(cfg, "LLM_TIMEOUT_S", 60)) * 2 + 30
        limit = int(getattr(cfg, "AI_CONCURRENCY_PER_USER", 2))
        if conc is not None:
            with conc.slot(f"score:u:{uid}", limit, ttl):
                out = gateway.score(
                    "writing",
                    lang=_lang(),
                    taskType=body.task_type,
                    prompt=body.prompt,
                    essay=essay,
                    metricsSummary=metrics_summary,
                )
        else:
            out = gateway.score(
                "writing",
                lang=_lang(),
                taskType=body.task_type,
                prompt=body.prompt,
                essay=essay,
                metricsSummary=metrics_summary,
            )
        llm_meta = out.pop("_meta_llm", None)
    except ApiError as e:
        # WS07-08: failed calls are accounted too — never a fabricated score.
        record_llm_usage(repo, cost_center="learner_scoring", op="score",
                         meta=None, user_id=uid, skill="writing",
                         status="failed", error_code=e.code)
        raise

    # WS07-08: append-only usage ledger row (never raises into the flow).
    record_llm_usage(repo, cost_center="learner_scoring", op="score",
                     meta=llm_meta, user_id=uid, skill="writing")

    # Attach metrics to the response (works in both stub and live mode)
    out["metrics"] = metrics

    # Persist the attempt for the Progress tab (history + trends).
    # WS05-08: provider/model/latency/token audit metadata rides into metrics.
    if llm_meta:
        metrics = dict(out.get("metrics") or {})
        metrics["llm"] = llm_meta
        out["metrics"] = metrics

    criteria_payload = {
        k: v for k, v in out.items()
        if k not in ("bands", "cefr", "metrics", "stub", "savedId", "score_metadata", "_meta_llm")
    }

    out["savedId"] = _repo().save_attempt(
        uid,
        type="writing",
        task=body.task_type or "",
        prompt=body.prompt or "",
        body=essay,
        bands=out.get("bands", {}),
        cefr=out.get("cefr", ""),
        metrics=out.get("metrics", {}),
        criteria=criteria_payload,
        score_metadata=out.get("score_metadata"),
    )

    # WS21 — WML qualifying event, emitted only after persistence succeeded.
    from app.routes._analytics import emit
    emit("writing_submitted", user_id=uid,
         task_type=body.task_type or "unknown")

    # gateway-defined shape; passthrough dict — shape validated client-side
    return jsonify(out), 200

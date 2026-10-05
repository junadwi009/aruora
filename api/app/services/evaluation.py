"""One evaluation implementation for HTTP development and queued production.

Rubrics, metrics, model selection and speaking evidence normalization are
unchanged. Queued completion persists the attempt and job result atomically.
No Flask request context is required by a worker.
"""
from __future__ import annotations
from contextlib import nullcontext
import re
import unicodedata
from sqlalchemy import select
from app.costguard import ensure_ai_available, record_llm_usage
from app.data.models import Attempt, Job, now
from app.domain.scoring import normalize_speaking_estimate
from app.errors import ApiError
from app.schemas import WritingEvaluateIn, SpeakingEvaluateIn
from app.services.essay_metrics import compute_metrics


def validate_size(kind, body, cfg):
    value = body.essay if kind == "writing" else body.transcript
    maximum = cfg.MAX_ESSAY_CHARS if kind == "writing" else cfg.MAX_TRANSCRIPT_CHARS
    if len(value) > maximum:
        raise ApiError("VALIDATION", f"Response is too long (max {maximum} characters)", 422)


def trusted_audio_features(jobs, job_id, uid, transcript):
    if not jobs or not job_id:
        return None
    st = jobs.get_status(job_id, uid)
    if not st or st.get("status") != "succeeded" or st.get("type") != "transcribe":
        return None
    result = st.get("result") or {}
    def normalize(value):
        return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", value).casefold()))
    source = normalize(result.get("transcript") or "")
    return result.get("features") if source and source == normalize(transcript) else None


def persist_result(repo, uid, kind, body, out, job_id=None):
    meta = out.get("score_metadata") or {}
    fields = dict(type=kind, task=(body.task_type if kind == "writing" else body.part) or "",
        prompt=(body.prompt if kind == "writing" else body.question) or "",
        body=body.essay if kind == "writing" else body.transcript,
        bands=out.get("bands", {}), cefr=out.get("cefr", ""), metrics=out.get("metrics", {}),
        criteria={k:v for k,v in out.items() if k not in
                  ("bands", "cefr", "metrics", "stub", "savedId", "score_metadata", "_meta_llm")})
    if not job_id:
        out["savedId"] = repo.save_attempt(uid, **fields, score_metadata=meta)
        return
    with repo.session_factory() as s:
        job = s.scalar(select(Job).where(Job.id == job_id, Job.user_id == uid).with_for_update())
        if job is None or job.status != "running":
            raise ApiError("JOB_OUTCOME_UNCERTAIN", "The evaluation can no longer be committed.", 409)
        attempt = Attempt(user_id=uid, **fields, **{key: meta.get(key) for key in (
            "score_method", "score_version", "model_provider", "model_id", "prompt_version",
            "rubric_version", "calibration_version")})
        s.add(attempt)
        s.flush()
        out["savedId"] = attempt.id
        job.result = dict(out)
        job.status = "succeeded"
        job.completed_at = now()
        job.payload = {}  # Pending raw input is no longer needed; history is the owned copy.
        llm = (out.get("metrics") or {}).get("llm") or {}
        job.provider = llm.get("provider")
        job.model_requested = llm.get("requestedModel")
        job.model_used = llm.get("resolvedModel") or llm.get("requestedModel")
        s.commit()


def evaluate(kind, body, ctx, uid, *, lang="en", job_id=None, metrics_fn=compute_metrics):
    repo, cfg, gateway = ctx["repo"], ctx["cfg"], ctx["gateway"]
    validate_size(kind, body, cfg)
    user = repo.get_user_by_id(uid)
    if user is None:
        raise ApiError("NOT_FOUND", "Account no longer exists", 404)
    if cfg.EMAIL_VERIFICATION_REQUIRED and not user.email_verified:
        raise ApiError("EMAIL_UNVERIFIED", "Verify your email address to use this feature", 403)
    ensure_ai_available(cfg, repo)
    conc = ctx.get("concurrency")
    slot = conc.slot(f"score:u:{uid}", int(cfg.AI_CONCURRENCY_PER_USER), 600) if conc else nullcontext()
    with slot:
        metrics = {}
        kw = {"lang": lang}
        if kind == "writing":
            metrics = metrics_fn(body.essay)
            mtld = metrics["lexicalDiversity"].get("mtld")
            mean = (metrics.get("syntax") or {}).get("meanSentenceLength")
            mtld_s = f"{mtld:.1f}" if mtld is not None else "N/A"
            mean_s = f"{mean:.1f}" if mean is not None else "N/A"
            kw.update(taskType=body.task_type, prompt=body.prompt, essay=body.essay,
                metricsSummary=(f"words={metrics['wordCount']}, "
                                f"FleschKincaidGrade={metrics['readability']['fleschKincaidGrade']}, "
                                f"MTLD={mtld_s}, meanSentenceLength={mean_s}"))
        else:
            kw.update(part=body.part, question=body.question, transcript=body.transcript)
        # Recheck immediately before inference, not only before CPU metrics.
        ensure_ai_available(cfg, repo)
        try:
            out = gateway.score(kind, **kw)
        except ApiError as exc:
            record_llm_usage(repo, cost_center="learner_scoring", op="score", meta=None,
                             user_id=uid, skill=kind, status="failed", error_code=exc.code)
            raise
        if kind == "speaking":
            out = normalize_speaking_estimate(out)
            metrics = dict(out.get("metrics") or {})
            audio = trusted_audio_features(ctx.get("jobs"), body.asrJobId, uid, body.transcript)
            if audio:
                metrics["audioFeatures"] = audio
            out["estimateScope"] = "speaking_text_estimate"
        llm_meta = out.pop("_meta_llm", None)
        record_llm_usage(repo, cost_center="learner_scoring", op="score", meta=llm_meta,
                         user_id=uid, skill=kind)
        if llm_meta:
            metrics["llm"] = llm_meta
        out["metrics"] = metrics
        persist_result(repo, uid, kind, body, out, job_id)
    # Best-effort telemetry from workers too; no learner content in properties.
    try:
        from app.domain.analytics import build_envelope
        props = {"task_type": body.task_type or "unknown"} if kind == "writing" else {"part": body.part or "unknown"}
        repo.save_analytics_event(build_envelope(f"{kind}_submitted", user_id=uid, properties=props))
    except Exception:
        pass
    return out


def score_job(payload, ctx):
    job = ctx["job"]  # Identity is from the stored server-owned job, never payload.
    kind = "writing" if job["type"] == "score_writing" else "speaking"
    schema = WritingEvaluateIn if kind == "writing" else SpeakingEvaluateIn
    body = schema.model_validate(payload["input"])
    out = evaluate(kind, body, ctx, job["userId"], lang=payload.get("lang", "en"), job_id=job["id"])
    return out, None

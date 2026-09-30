"""Server-authoritative short-practice grading; never synthesizes IELTS bands.

Only opaque practiceId + answer strings cross the submission boundary. A server
snapshot fixes the answer key and question order. An atomic claim plus attempt
insert and result write share ONE transaction; retries return the same savedId.
"""
from __future__ import annotations
import hashlib
import json
import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, delete, func
from app.errors import ApiError

METHOD = "practice-accuracy-v1"
SKILLS = ("reading", "listening")
LEVELS = ("A1A2", "A2", "B1", "B2", "C1", "C2")


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold().strip()
    text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    return re.sub(r"\s+", " ", text)


def validate_snapshot(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ApiError("POOL_INVALID", "Practice content is unavailable", 503)
    questions = payload.get("questions")
    if not isinstance(questions, list) or not 1 <= len(questions) <= 40:
        raise ApiError("POOL_INVALID", "Practice content is unavailable", 503)
    clean = {}
    for field, ceiling in (("title", 200), ("passage", 22000), ("transcript", 14000)):
        value = payload.get(field, "")
        if not isinstance(value, str) or len(value) > ceiling:
            raise ApiError("POOL_INVALID", "Practice content is unavailable", 503)
        clean[field] = value
    clean["questions"] = []
    for q in questions:
        if not isinstance(q, dict):
            raise ApiError("POOL_INVALID", "Practice content is unavailable", 503)
        item = {}
        for key, ceiling in (("stem", 1000), ("answer", 300), ("explanation", 1200)):
            value = q.get(key, "")
            if not isinstance(value, str) or len(value) > ceiling or (key != "explanation" and not value.strip()):
                raise ApiError("POOL_INVALID", "Practice content is unavailable", 503)
            item[key] = value
        options = q.get("options")
        if options is not None:
            if (not isinstance(options, list) or not 2 <= len(options) <= 8
                or any(not isinstance(x, str) or not x.strip() or len(x) > 500 for x in options)
                or len({normalize(x) for x in options}) != len(options)
                or normalize(item["answer"]) not in {normalize(x) for x in options}):
                raise ApiError("POOL_INVALID", "Practice content is unavailable", 503)
            item["options"] = options[:]
        clean["questions"].append(item)
    return clean


def public_task(row, *, repeat=False) -> dict:
    snapshot = row.snapshot
    # Explicit allowlist, NOT strip-by-key: unknown nested metadata cannot leak.
    return {"practiceId": row.id, "skill": row.skill, "difficulty": row.band,
            "title": snapshot["title"], "passage": snapshot["passage"],
            "transcript": snapshot["transcript"], "repeat": bool(repeat),
            "expiresAt": row.expires_at.isoformat(), "scoringMethod": METHOD,
            "questions": [{"stem": q["stem"], **({"options": q["options"]} if q.get("options") else {})}
                          for q in snapshot["questions"]]}


def start(session_factory, uid: int, skill: str, band: str, payload: dict,
          *, repeat=False, now: datetime | None = None) -> dict:
    from app.data.models import PracticeSession
    from app.data.models import UserProfile
    if skill not in SKILLS or band not in LEVELS:
        raise ApiError("VALIDATION", "Unsupported practice skill or level", 422)
    snapshot = validate_snapshot(payload)
    now = now or datetime.now(timezone.utc)
    with session_factory() as s:
        # PostgreSQL serializes concurrent start quotas on the owning account.
        owner = s.execute(select(UserProfile.id).where(UserProfile.id == uid).with_for_update()).scalar_one_or_none()
        if owner is None:
            raise ApiError("UNAUTHORIZED", "Sign in to continue", 401)
        active = s.execute(select(func.count()).select_from(PracticeSession).where(
            PracticeSession.user_id == uid, PracticeSession.status == "open",
            PracticeSession.expires_at > now)).scalar_one()
        if active >= 8:
            raise ApiError("PRACTICE_LIMIT", "Finish or close an open practice first", 429)
        row = PracticeSession(id=secrets.token_hex(16), user_id=uid, skill=skill,
                              band=band, snapshot=snapshot, status="open",
                              created_at=now, expires_at=now + timedelta(hours=2))
        s.add(row)
        s.flush()
        output = public_task(row, repeat=repeat)
        s.commit()
        return output


def validate_submission(body) -> tuple[str, list[str]]:
    if not isinstance(body, dict) or set(body) != {"practiceId", "answers"}:
        raise ApiError("VALIDATION", "Send practiceId and answers only; client scores are not accepted", 422)
    pid, answers = body["practiceId"], body["answers"]
    if not isinstance(pid, str) or not re.fullmatch(r"[a-f0-9]{32}", pid):
        raise ApiError("VALIDATION", "Invalid practice identifier", 422)
    if not isinstance(answers, list) or not 1 <= len(answers) <= 40 or any(
        not isinstance(a, str) or len(a) > 300 for a in answers):
        raise ApiError("VALIDATION", "Invalid answer list", 422)
    return pid, answers


def grade(snapshot: dict, answers: list[str]) -> dict:
    questions = snapshot["questions"]
    if len(answers) != len(questions):
        raise ApiError("VALIDATION", "Answer count does not match this practice", 422)
    review = []
    for i, (q, answer) in enumerate(zip(questions, answers)):
        correct = bool(normalize(answer)) and normalize(answer) == normalize(q["answer"])
        review.append({"index": i, "stem": q["stem"], "submitted": answer,
                       "correct": correct, "expected": q["answer"],
                       "explanation": q.get("explanation", "")})
    count = sum(x["correct"] for x in review)
    return {"correct": count, "total": len(review),
            "accuracyPct": round(100 * count / len(review), 1),
            "scoringMethod": METHOD, "review": review,
            "disclaimer": "Short-practice accuracy, not an IELTS band estimate."}


def submit(session_factory, uid: int, body, *, now: datetime | None = None) -> tuple[dict, bool]:
    from app.data.models import PracticeSession
    from app.data.models import Attempt
    pid, answers = validate_submission(body)
    digest = hashlib.sha256(json.dumps(answers, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    now = now or datetime.now(timezone.utc)
    with session_factory() as s:
        claimed = s.execute(update(PracticeSession).where(
            PracticeSession.id == pid, PracticeSession.user_id == uid,
            PracticeSession.status == "open", PracticeSession.expires_at > now,
        ).values(status="grading").returning(
            PracticeSession.snapshot, PracticeSession.skill, PracticeSession.band,
        )).first()
        if claimed is None:
            row = s.execute(select(PracticeSession).where(
                PracticeSession.id == pid, PracticeSession.user_id == uid,
            )).scalar_one_or_none()
            if row is None:
                raise ApiError("NOT_FOUND", "Practice not found", 404)
            if row.status == "submitted":
                if row.answer_hash != digest:
                    raise ApiError("SUBMISSION_CONFLICT", "This practice was already submitted with different answers", 409)
                return dict(row.result), False
            raise ApiError("PRACTICE_EXPIRED", "This practice is closed or has expired", 410)
        snapshot, skill, difficulty = claimed
        result = grade(snapshot, answers)
        # Empty bands deliberately excludes these results from readiness estimates.
        attempt = Attempt(user_id=uid, type=skill,
                          task=f"{result['correct']}/{result['total']}",
                          prompt=snapshot["title"], body="", bands={}, cefr="",
                          criteria={"practiceResult": result},
                          metrics={"correct": result["correct"], "total": result["total"],
                                   "accuracyPct": result["accuracyPct"], "difficulty": difficulty,
                                   "scoringMethod": METHOD},
                          score_method="server_accuracy", score_version=METHOD)
        s.add(attempt)
        s.flush()
        result = {**result, "savedId": attempt.id, "practiceId": pid, "skill": skill}
        s.execute(update(PracticeSession).where(PracticeSession.id == pid, PracticeSession.user_id == uid)
                  .values(status="submitted", answer_hash=digest, result=result))
        s.commit()
        return result, True


def close(session_factory, uid: int, pid: str) -> None:
    from app.data.models import PracticeSession
    with session_factory() as s:
        found = s.execute(select(PracticeSession.id).where(PracticeSession.id == pid,
                                                           PracticeSession.user_id == uid)).scalar_one_or_none()
        if found is None:
            raise ApiError("NOT_FOUND", "Practice not found", 404)
        s.execute(update(PracticeSession).where(PracticeSession.id == pid,
                    PracticeSession.user_id == uid, PracticeSession.status == "open").values(status="closed"))
        s.commit()


def export_sessions(session, uid: int) -> list[dict]:
    from app.data.models import PracticeSession
    rows = session.execute(select(PracticeSession).where(PracticeSession.user_id == uid)).scalars()
    return [{"practiceId": r.id, "skill": r.skill, "difficulty": r.band, "status": r.status,
             "createdAt": r.created_at.isoformat(), "expiresAt": r.expires_at.isoformat(),
             "result": r.result if r.status == "submitted" else None} for r in rows]


def purge(session_factory, now: datetime) -> int:
    from app.data.models import PracticeSession
    with session_factory() as s:
        n = s.execute(delete(PracticeSession).where(
            PracticeSession.expires_at < now - timedelta(days=1))).rowcount
        s.commit()
        return int(n or 0)

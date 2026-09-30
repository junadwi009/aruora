"""v1.2 identity and transaction invariants; no framework dependency.

These helpers never authenticate on an email string alone. The caller supplies
an authoritative database user and server-side session, not request JSON.
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from sqlalchemy import update


def verified_admin(user, cfg) -> bool:
    if user is None or getattr(user, "email_verified", False) is not True:
        return False
    email = getattr(user, "email", None)
    if not isinstance(email, str) or not email.strip():
        return False
    allowed = {str(e).strip().casefold() for e in cfg.ADMIN_EMAILS}
    return email.strip().casefold() in allowed


def inherited_flags(flags) -> dict:
    # An app-wide gate grant may survive login. Identity-bound privileges may not.
    return {"gate": True} if isinstance(flags, dict) and flags.get("gate") is True else {}


def reauth_age(flags, now: datetime) -> float | None:
    try:
        stamp = datetime.fromisoformat(flags.get("reauth_at", ""))
        if stamp.tzinfo is None or now.tzinfo is None:
            return None
        age = (now - stamp).total_seconds()
        return age if age >= 0 else None
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def mfa_proof(uid: int, secret: str) -> dict:
    return {"admin_mfa_uid": uid,
            "admin_mfa_policy": hashlib.sha256(secret.encode()).hexdigest()}


def admin_session(user, row, cfg) -> bool:
    if not verified_admin(user, cfg) or row is None or row.user_id != user.id:
        return False
    secret = getattr(cfg, "ADMIN_TOTP_SECRET", "")
    if not secret:
        return True
    expected = mfa_proof(user.id, secret)
    flags = row.flags if isinstance(row.flags, dict) else {}
    return all(flags.get(k) == v for k, v in expected.items())


def consume_token(session_factory, model, kind: str, raw: str,
                  now: datetime | None = None) -> int | None:
    """One conditional write: concurrent consumers cannot both win.

    UPDATE..RETURNING is supported by the project's SQLite/PostgreSQL profile.
    Unknown kinds, malformed/overlong input, expired and used tokens fail closed.
    """
    if kind not in ("reset", "verify") or not isinstance(raw, str) or not 1 <= len(raw) <= 512:
        return None
    now = now or datetime.now(timezone.utc)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with session_factory() as s:
        uid = s.execute(update(model).where(
            model.token_hash == digest, model.kind == kind,
            model.used_at.is_(None), model.expires_at > now,
        ).values(used_at=now).returning(model.user_id)).scalar_one_or_none()
        s.commit()
        return uid

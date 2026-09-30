"""Repository facade — Data layer only.

All methods open a short-lived session via self._sf(), commit writes,
and return plain dicts or detached ORM objects.  No business logic here.
"""

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update


def task_pool_hash(payload: dict) -> str:
    """Stable content hash of a Task Bank payload (WS07 dedup/UNIQUE arbiter).

    Canonical JSON: sorted keys, compact separators — the same validated task
    always hashes identically regardless of dict insertion order."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
from sqlalchemy import delete as sa_delete
from sqlalchemy.exc import IntegrityError

from .models import (
    Attempt,
    AiUsageLedger,
    AnalyticsEvent,
    Card,
    Feedback,
    GenUsage,
    GeneratedSet,
    Job,
    Lesson,
    Milestone,
    Mock,
    PlacementAttempt,
    PlacementCombo,
    PlacementItem,
    Program,
    SkillLevel,
    SystemFlag,
    TaskExposure,
    TestGate,
    UserProfile,
    now,
)


class Repository:
    def __init__(self, session_factory):
        self._sf = session_factory

    @property
    def session_factory(self):
        """The underlying sessionmaker — lets the WS03 SessionStore share the
        exact same engine/transaction scope as the repository (test DI path)."""
        return self._sf

    # ── User ──────────────────────────────────────────────────────────────────

    def create_user(
        self,
        name: str,
        goal: str,
        target_band: float,
        skill_targets: dict,
        exam_date: str | None = None,
    ) -> UserProfile:
        """Insert a new UserProfile and return the detached object (with .id)."""
        with self._sf() as s:
            u = UserProfile(
                name=name,
                goal=goal,
                target_band=target_band,
                skill_targets=skill_targets,
                exam_date=exam_date,
            )
            s.add(u)
            s.commit()
            s.refresh(u)
            s.expunge(u)
        return u

    # ── Accounts (Phase 3a) ───────────────────────────────────────────────────

    def create_account(self, email, password, name="", goal="other", target_band=6.0,
                       skill_targets=None) -> UserProfile:
        from app.security.passwords import hash_password
        with self._sf() as s:
            u = UserProfile(
                name=name, goal=goal, target_band=target_band,
                skill_targets=skill_targets or {},
                email=email, password_hash=hash_password(password),
            )
            s.add(u)
            s.commit()
            s.refresh(u)
            s.expunge(u)
        return u

    def attach_credentials(self, user_id, email, password) -> UserProfile:
        from app.security.passwords import hash_password
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            u.email = email
            u.password_hash = hash_password(password)
            s.commit()
            s.refresh(u)
            s.expunge(u)
        return u

    def upsert_google_user(self, sub: str, email: str = "", name: str = "",
                           email_verified: bool = False) -> tuple[UserProfile, bool]:
        """Find a user by google_sub; else link to an existing same-email account;
        else create a new (password-less) account. Returns (detached user, is_new)
        where is_new is True only when a brand-new account was created for this sub
        (i.e. first-ever Google sign-in, not a link to an existing email account).

        WS03-05: `email` is only passed when Google asserted `email_verified`,
        and the adopted address is marked verified."""
        with self._sf() as s:
            row = s.execute(
                select(UserProfile).where(UserProfile.google_sub == sub)
            ).scalars().first()
            is_new = False
            if row is None and email:
                row = s.execute(
                    select(UserProfile).where(UserProfile.email == email)
                ).scalars().first()
                if row is not None:
                    from app.security.input_contracts import authorize_google_link
                    authorize_google_link(row, sub)
                    row.google_sub = sub  # only an already-verified local account may auto-link
            if row is None:
                row = UserProfile(
                    name=name or "", goal="other", target_band=6.0, skill_targets={},
                    email=email or None, google_sub=sub, email_verified=bool(email and email_verified),
                )
                s.add(row)
                is_new = True
            elif name and not row.name:
                row.name = name
            s.commit()
            s.refresh(row)
            s.expunge(row)
        return row, is_new

    def has_password(self, user_id) -> bool:
        """True when the account has a local password set (vs Google-only)."""
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            return bool(u and u.password_hash)

    def get_account_by_email(self, email) -> UserProfile | None:
        with self._sf() as s:
            row = s.execute(
                select(UserProfile).where(UserProfile.email == email)
            ).scalars().first()
            if row is None:
                return None
            s.refresh(row)
            s.expunge(row)
        return row

    def verify_login(self, email, password) -> UserProfile | None:
        from app.security.passwords import verify_password
        u = self.get_account_by_email(email)
        if u is None or not u.password_hash or not verify_password(u.password_hash, password):
            return None
        return u

    def set_password(self, user_id, password) -> None:
        from app.security.passwords import hash_password
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            u.password_hash = hash_password(password)
            s.commit()

    def change_password(self, user_id, current, new) -> bool:
        """Verify `current` then set `new`. False if current is wrong."""
        from app.security.passwords import verify_password, hash_password
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            if u is None or not u.password_hash or not verify_password(u.password_hash, current):
                return False
            u.password_hash = hash_password(new)
            s.commit()
            return True

    def verify_password_for(self, user_id, password) -> bool:
        """Password check without changing anything (admin reauthentication)."""
        from app.security.passwords import verify_password
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            return bool(u and u.password_hash and verify_password(u.password_hash, password))

    def set_email_verified(self, user_id, verified: bool = True) -> None:
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            if u is not None:
                u.email_verified = bool(verified)
                s.commit()

    # ── WS03-05/06: single-use tokens (password reset, email verification) ────

    def create_one_time_token(self, kind: str, user_id: int, ttl_min: int,
                              ip_hash: str = "", ua: str = "") -> str:
        """Create a single-use expiring token; returns the RAW token (only the
        sha256 hash is persisted). Any outstanding token of the same kind for
        the user is invalidated first, so at most one live link exists."""
        import hashlib
        import secrets
        from .models import AuthOneTimeToken
        raw = secrets.token_urlsafe(32)
        now_utc = datetime.now(timezone.utc)
        with self._sf() as s:
            s.execute(
                update(AuthOneTimeToken)
                .where(AuthOneTimeToken.kind == kind,
                       AuthOneTimeToken.user_id == user_id,
                       AuthOneTimeToken.used_at.is_(None))
                .values(used_at=now_utc)
            )
            s.add(AuthOneTimeToken(
                kind=kind, user_id=user_id,
                token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                expires_at=now_utc + timedelta(minutes=ttl_min),
                request_ip_hash=ip_hash, request_ua=(ua or "")[:200],
            ))
            s.commit()
        return raw

    def consume_one_time_token(self, kind: str, raw: str) -> int | None:
        from app.security.audit_integrity import consume_token
        from .models import AuthOneTimeToken
        return consume_token(self._sf, AuthOneTimeToken, kind, raw)

    def invalidate_one_time_tokens(self, user_id: int, kinds: tuple[str, ...]) -> None:
        """Mark every outstanding token of `kinds` for the user as used."""
        from .models import AuthOneTimeToken
        with self._sf() as s:
            s.execute(
                update(AuthOneTimeToken)
                .where(AuthOneTimeToken.user_id == user_id,
                       AuthOneTimeToken.used_at.is_(None),
                       AuthOneTimeToken.kind.in_(kinds))
                .values(used_at=datetime.now(timezone.utc))
            )
            s.commit()

    # ── WS03-07: append-only admin audit trail ────────────────────────────────

    def add_audit(self, action: str, *, actor_user_id=None, actor_email: str = "",
                  target_user_id=None, detail: dict | None = None, ip_hash: str = "") -> None:
        from .models import AdminAudit
        with self._sf() as s:
            s.add(AdminAudit(
                actor_user_id=actor_user_id, actor_email=actor_email or "",
                action=action, target_user_id=target_user_id,
                detail=detail or {}, ip_hash=ip_hash or "",
            ))
            s.commit()

    def list_audit(self, limit: int = 100) -> list[dict]:
        from .models import AdminAudit
        with self._sf() as s:
            rows = s.execute(
                select(AdminAudit).order_by(AdminAudit.id.desc()).limit(limit)
            ).scalars().all()
            return [{
                "id": r.id, "actorEmail": r.actor_email,
                "actorUserId": r.actor_user_id, "action": r.action,
                "targetUserId": r.target_user_id, "detail": r.detail or {},
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            } for r in rows]

    def complete_onboarding(self, user_id: int, *, name: str, goal: str,
                            target_band: float, skill_targets: dict | None = None,
                            exam_date: str | None = None) -> UserProfile | None:
        """Update the session owner's learning fields without replacing identity.

        No credential/auth fields are writable through this method. An absent
        optional field is preserved, not silently reset to an empty value.
        """
        with self._sf() as s:
            user = s.execute(
                select(UserProfile).where(UserProfile.id == user_id)
            ).scalars().first()
            if user is None:
                return None
            user.name = name
            user.goal = goal
            user.target_band = target_band
            if skill_targets is not None:
                user.skill_targets = skill_targets
            if exam_date is not None:
                user.exam_date = exam_date
            s.commit()
            s.refresh(user)
            s.expunge(user)
            return user

    def update_profile(self, user_id, fields: dict) -> None:
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            for col in ("name", "country", "bio"):
                if fields.get(col) is not None:
                    setattr(u, col, fields[col])
            if fields.get("examDate") is not None:
                u.exam_date = fields["examDate"]
            if fields.get("targetBand") is not None:
                u.target_band = float(fields["targetBand"])
            if fields.get("skillTargets") is not None:
                u.skill_targets = fields["skillTargets"]
            if "reminderTime" in fields:  # "" or null clears it
                u.reminder_time = fields["reminderTime"] or None
            if "reminderTz" in fields:  # IANA tz; "" or null clears it
                u.reminder_tz = fields["reminderTz"] or None
            s.commit()

    def due_reminders(self, now_utc, default_tz: str = "UTC") -> list[dict]:
        """Users whose LOCAL reminder hour matches the current local hour and who
        haven't been emailed on their local date yet.

        Each user's local time is computed from their `reminder_tz` (falling back
        to `default_tz`, then UTC). Returns each due user's local `date` so the
        caller marks 'sent' against the correct calendar day for that timezone.
        """
        from zoneinfo import ZoneInfo

        def _zone(name):
            try:
                return ZoneInfo(name) if name else None
            except Exception:
                return None

        default_zone = _zone(default_tz) or ZoneInfo("UTC")
        with self._sf() as s:
            rows = s.execute(
                select(UserProfile).where(UserProfile.reminder_time.is_not(None))
            ).scalars().all()
            out = []
            for u in rows:
                if not u.email or not u.reminder_time:
                    continue
                try:
                    rh = int(u.reminder_time.split(":")[0])
                except (ValueError, IndexError):
                    continue
                local = now_utc.astimezone(_zone(u.reminder_tz) or default_zone)
                local_date = local.date().isoformat()
                if local.hour == rh and u.reminder_last_sent != local_date:
                    out.append({"id": u.id, "email": u.email, "name": u.name, "date": local_date})
            return out

    def mark_reminder_sent(self, user_id: int, today: str) -> None:
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            u.reminder_last_sent = today
            s.commit()

    def set_avatar(self, user_id, data_url: str) -> None:
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            u.avatar = data_url
            s.commit()

    def export_data(self, user_id) -> dict:
        """All of this user's data as plain JSON-able dicts (data portability).

        WS04-07: contains ONLY this user's rows; excludes secrets (password
        hash, google_sub) and internal counters (gen_usage/test_gate) which are
        not portable product data — see the ownership inventory document.
        """
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            profile = {"id": u.id, "email": u.email, "name": u.name, "goal": u.goal,
                       "targetBand": u.target_band, "skillTargets": u.skill_targets,
                       "country": u.country, "examDate": u.exam_date, "bio": u.bio,
                       "avatar": u.avatar} if u else {}
            def dump(model, **w):
                rows = s.execute(select(model).where(*[getattr(model, k) == v for k, v in w.items()])).scalars().all()
                out = []
                for r in rows:
                    d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
                    for k, v in list(d.items()):
                        if hasattr(v, "isoformat"):
                            d[k] = v.isoformat()
                    out.append(d)
                return out
            programs = dump(Program, user_id=user_id)
            milestones = []
            for p in programs:
                milestones += dump(Milestone, program_id=p["id"])
            return {
                "profile": profile,
                "practiceSessions": __import__("app.services.practice_integrity", fromlist=["export_sessions"]).export_sessions(s, user_id),
                "skillLevels": dump(SkillLevel, user_id=user_id),
                "attempts": dump(Attempt, user_id=user_id),
                "mocks": dump(Mock, user_id=user_id),
                "cards": dump(Card, user_id=user_id),
                "lessons": dump(Lesson, user_id=user_id),
                "programs": programs,
                "milestones": milestones,
                "placementAttempts": dump(PlacementAttempt, user_id=user_id),
                # The learner's own authored feedback text is their content.
                "feedback": [
                    {"stars": f.stars, "insight": f.insight,
                     "createdAt": f.created_at.isoformat() if f.created_at else None}
                    for f in s.execute(
                        select(Feedback).where(Feedback.user_id == user_id)
                    ).scalars().all()
                ],
            }

    def delete_account(self, user_id) -> bool:
        """Delete the account and every row they own.

        WS04-04/07: child data disappears through ON DELETE CASCADE declared on
        the FKs (including milestones via programs), so no hand-maintained list
        of child tables can rot. Idempotent from the caller's perspective;
        returns False only when the profile no longer exists.
        """
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            if u is None:
                return False
            s.delete(u)
            s.commit()
            return True

    # ── Admin (Manage users) ──────────────────────────────────────────────────

    def list_accounts(self, limit: int = 200) -> list[dict]:
        """Registered accounts (email not null), oldest first, with usage counts.

        WS04-06: admin-only method with pagination and minimal returned fields
        (no password hashes / google_sub / session identifiers).
        """
        limit = max(1, min(int(limit), 500))
        with self._sf() as s:
            users = s.execute(
                select(UserProfile)
                .where(UserProfile.email.is_not(None))
                .order_by(UserProfile.id)
                .limit(limit)
            ).scalars().all()
            out = []
            for u in users:
                n_att = s.execute(
                    select(func.count(Attempt.id)).where(Attempt.user_id == u.id)
                ).scalar() or 0
                out.append({
                    "id": u.id,
                    "email": u.email,
                    "name": u.name,
                    "targetBand": u.target_band,
                    "country": u.country,
                    "examDate": u.exam_date,
                    "attempts": int(n_att),
                    "createdAt": u.created_at.isoformat() if u.created_at else None,
                })
            return out

    def admin_stats(self) -> dict:
        """Instance-wide totals for the admin dashboard."""
        with self._sf() as s:
            total_profiles = s.execute(select(func.count(UserProfile.id))).scalar() or 0
            total_accounts = s.execute(
                select(func.count(UserProfile.id)).where(UserProfile.email.is_not(None))
            ).scalar() or 0
            total_attempts = s.execute(select(func.count(Attempt.id))).scalar() or 0
            total_mocks = s.execute(select(func.count(Mock.id))).scalar() or 0
            total_cards = s.execute(select(func.count(Card.id))).scalar() or 0
            return {
                "totalAccounts": int(total_accounts),
                "totalProfiles": int(total_profiles),
                "anonymousProfiles": int(total_profiles) - int(total_accounts),
                "totalAttempts": int(total_attempts),
                "totalMocks": int(total_mocks),
                "totalCards": int(total_cards),
            }

    def get_user_by_id(self, user_id) -> UserProfile | None:
        with self._sf() as s:
            row = s.get(UserProfile, user_id)
            if row is None:
                return None
            s.refresh(row)
            s.expunge(row)
        return row

    def get_user(self) -> UserProfile | None:
        """Return the most recently created UserProfile, or None."""
        with self._sf() as s:
            row = (
                s.execute(
                    select(UserProfile).order_by(UserProfile.id.desc()).limit(1)
                )
                .scalars()
                .first()
            )
            if row is None:
                return None
            s.refresh(row)
            s.expunge(row)
        return row

    # ── Skill levels ─────────────────────────────────────────────────────────

    def set_skill_level(self, user_id: int, skill: str, band: str) -> None:
        """UPSERT: update band+updated_at if row exists, else insert."""
        with self._sf() as s:
            existing = (
                s.execute(
                    select(SkillLevel).where(
                        SkillLevel.user_id == user_id,
                        SkillLevel.skill == skill,
                    )
                )
                .scalars()
                .first()
            )
            if existing:
                existing.band = band
                existing.updated_at = datetime.now(timezone.utc)
            else:
                s.add(SkillLevel(user_id=user_id, skill=skill, band=band))
            s.commit()

    def get_skill_levels(self, user_id: int) -> list[tuple[str, str]]:
        """Return list of (skill, band) for the user."""
        with self._sf() as s:
            rows = (
                s.execute(
                    select(SkillLevel).where(SkillLevel.user_id == user_id)
                )
                .scalars()
                .all()
            )
            return [(r.skill, r.band) for r in rows]

    # ── Placement combos ─────────────────────────────────────────────────────

    def get_combo(self, combo_id: int) -> dict:
        """Return combo dict with camelCase keys.  Raise KeyError if not found."""
        with self._sf() as s:
            combo = s.get(PlacementCombo, combo_id)
            if combo is None:
                raise KeyError(f"combo_id {combo_id!r} not found")
            items = (
                s.execute(
                    select(PlacementItem).where(PlacementItem.combo_id == combo_id)
                )
                .scalars()
                .all()
            )
            return {
                "comboId": combo.combo_id,
                "targetMinutes": combo.target_minutes,
                "sections": combo.sections,
                "items": [
                    {
                        "id": it.id,
                        "skill": it.skill,
                        "bandTag": it.band_tag,
                        "type": it.type,
                        "payload": it.payload,
                        "sectionSeconds": it.section_seconds,
                    }
                    for it in items
                ],
            }

    def list_combo_ids(self) -> list[int]:
        """All combo_ids present, sorted ascending."""
        with self._sf() as s:
            rows = s.execute(
                select(PlacementCombo.combo_id).order_by(PlacementCombo.combo_id)
            ).scalars().all()
            return list(rows)

    # ── Placement attempts ────────────────────────────────────────────────────

    def save_placement_attempt(
        self,
        user_id: int,
        combo_id: int,
        duration_sec: int,
        per_skill: dict,
        overall_band: float,
        cefr: str,
        gap_to_target: float,
    ) -> int:
        """Insert a PlacementAttempt and return its id."""
        with self._sf() as s:
            attempt = PlacementAttempt(
                user_id=user_id,
                combo_id=combo_id,
                duration_sec=duration_sec,
                per_skill=per_skill,
                overall_band=overall_band,
                cefr=cefr,
                gap_to_target=gap_to_target,
            )
            s.add(attempt)
            s.commit()
            s.refresh(attempt)
            return attempt.id

    # ── Generated sets ────────────────────────────────────────────────────────

    def serve_set(self, skill: str, band: str) -> dict | None:
        """Return ONE random ACTIVE GeneratedSet.payload for (skill, band), or None.
        Quarantined/retired inventory is never served (WS27 lifecycle)."""
        with self._sf() as s:
            rows = (
                s.execute(
                    select(GeneratedSet).where(
                        GeneratedSet.skill == skill,
                        GeneratedSet.band == band,
                        GeneratedSet.status == "active",
                    )
                )
                .scalars()
                .all()
            )
            if not rows:
                return None
            return random.choice(rows).payload

    def serve_any_set(self, skill: str) -> dict | None:
        """Return ONE random ACTIVE GeneratedSet.payload for the skill (any band),
        or None. Quarantined/retired inventory is never served (WS27)."""
        with self._sf() as s:
            rows = (
                s.execute(
                    select(GeneratedSet).where(
                        GeneratedSet.skill == skill,
                        GeneratedSet.status == "active",
                    )
                )
                .scalars()
                .all()
            )
            if not rows:
                return None
            return random.choice(rows).payload

    # ── WS27: Task Bank lifecycle + per-user exposure ─────────────────────────

    def list_active_sets(self, skill: str, band: str | None = None) -> list[tuple]:
        """Lightweight active-inventory rows [(id, payload, serve_count)] for a
        bucket (or the whole skill when band is None — adjacent fallback)."""
        with self._sf() as s:
            q = select(
                GeneratedSet.id, GeneratedSet.payload, GeneratedSet.serve_count
            ).where(
                GeneratedSet.skill == skill,
                GeneratedSet.status == "active",
            )
            if band is not None:
                q = q.where(GeneratedSet.band == band)
            return [(r[0], r[1], r[2]) for r in s.execute(q).all()]

    def band_of_set(self, set_id: int) -> str | None:
        with self._sf() as s:
            return s.execute(
                select(GeneratedSet.band).where(GeneratedSet.id == set_id)
            ).scalar_one_or_none()

    def recent_exposure_map(self, user_id: int) -> dict[int, datetime]:
        """Last served_at per set_id for this user (anti-repeat selection)."""
        with self._sf() as s:
            rows = s.execute(
                select(TaskExposure.set_id, TaskExposure.served_at).where(
                    TaskExposure.user_id == user_id
                )
            ).all()
            return {r[0]: self._utc_naive(r[1]) for r in rows if r[1] is not None}

    def record_exposure(self, user_id: int, set_id: int, context: str,
                        repeat: bool) -> None:
        with self._sf() as s:
            s.add(TaskExposure(user_id=user_id, set_id=set_id,
                               served_at=now(), selection_context=context[:20],
                               repeat=repeat))
            s.commit()

    def increment_serve_count(self, set_id: int) -> None:
        with self._sf() as s:
            gs = s.get(GeneratedSet, set_id)
            if gs is not None:
                gs.serve_count = (gs.serve_count or 0) + 1
                s.commit()

    def find_set_by_hash(self, skill: str, band: str, content_hash: str) -> bool:
        """Exact-duplicate probe within a bucket (27 §14 layer 1)."""
        if not content_hash:
            return False
        with self._sf() as s:
            return s.execute(
                select(GeneratedSet.id).where(
                    GeneratedSet.skill == skill,
                    GeneratedSet.band == band,
                    GeneratedSet.content_hash == content_hash,
                )
            ).first() is not None

    def quarantine_set(self, set_id: int, flags: list[str]) -> None:
        """Quarantined inventory is auditable but never servable."""
        with self._sf() as s:
            gs = s.get(GeneratedSet, set_id)
            if gs is not None:
                gs.status = "quarantined"
                gs.quality_flags = {"flags": flags[:20]}
                s.commit()

    def retire_set(self, set_id: int) -> None:
        with self._sf() as s:
            gs = s.get(GeneratedSet, set_id)
            if gs is not None:
                gs.status = "retired"
                gs.retired_at = now()
                s.commit()

    def count_active_sets(self, skill: str, band: str) -> int:
        """Active inventory in a bucket — the replenishment threshold signal
        (quarantined/retired rows never count, 27 §12)."""
        with self._sf() as s:
            return int(s.execute(
                select(func.count()).select_from(GeneratedSet).where(
                    GeneratedSet.skill == skill,
                    GeneratedSet.band == band,
                    GeneratedSet.status == "active",
                )
            ).scalar_one() or 0)

    def job_backlog(self) -> list[dict]:
        """Pending/running job counts per queue+status (queue-age gauges)."""
        with self._sf() as s:
            rows = s.execute(
                select(Job.queue, Job.status, func.count()).where(
                    Job.status.in_(["queued", "running"])
                ).group_by(Job.queue, Job.status)
            ).all()
            return [{"queue": r[0], "status": r[1], "count": int(r[2])}
                    for r in rows]

    def pool_inventory(self) -> list[dict]:
        """Per-bucket inventory counters (active/quarantined/retired) for the
        pool-health dashboard (27 §21)."""
        with self._sf() as s:
            rows = s.execute(
                select(
                    GeneratedSet.skill,
                    GeneratedSet.band,
                    GeneratedSet.status,
                    func.count(),
                    func.coalesce(func.sum(GeneratedSet.serve_count), 0),
                ).group_by(
                    GeneratedSet.skill, GeneratedSet.band, GeneratedSet.status
                )
            ).all()
            return [
                {"skill": r[0], "band": r[1], "status": r[2],
                 "count": int(r[3]), "serves": int(r[4])}
                for r in rows
            ]

    def add_task_bank_set(
        self,
        skill: str,
        band: str,
        payload: dict,
        *,
        source: str = "generated",
        status: str = "active",
        content_hash: str | None = None,
        quality_flags: dict | None = None,
        generation_meta: dict | None = None,
        gen_cost_micros: int | None = None,
        pool_kind: str = "practice_adaptive",
    ) -> int | None:
        """Insert a Task Bank row post-validation. Returns None when an exact
        duplicate already exists in the bucket (UNIQUE index arbitrates races).
        Activation timestamp is set only for rows entering as active."""
        content_hash = content_hash or task_pool_hash(payload)
        with self._sf() as s:
            idx = s.execute(
                select(func.count()).select_from(GeneratedSet).where(
                    GeneratedSet.skill == skill, GeneratedSet.band == band
                )
            ).scalar_one()
            row = GeneratedSet(
                skill=skill, band=band, set_index=idx, payload=payload,
                source=source, status=status, content_hash=content_hash,
                quality_flags=quality_flags or {},
                generation_meta=generation_meta or {},
                gen_cost_micros=gen_cost_micros,
                pool_kind=pool_kind,
                activated_at=now() if status == "active" else None,
            )
            s.add(row)
            try:
                s.commit()
            except IntegrityError:
                s.rollback()
                return None
            s.refresh(row)
            return row.id

    # ── Test-phase gate + feedback ─────────────────────────────────────────────

    def gate_get(self, uid: int) -> dict:
        with self._sf() as s:
            g = s.get(TestGate, uid)
            if g is None:
                g = TestGate(user_id=uid, active_seconds=0)
                s.add(g)
                s.commit()
                s.refresh(g)
            return {"active_seconds": g.active_seconds, "unlocked_at": g.unlocked_at}

    def gate_add_seconds(self, uid: int, secs: int) -> int:
        with self._sf() as s:
            g = s.get(TestGate, uid)
            if g is None:
                g = TestGate(user_id=uid, active_seconds=0)
                s.add(g)
            g.active_seconds = (g.active_seconds or 0) + max(0, int(secs))
            s.commit()
            return g.active_seconds

    def gate_unlock(self, uid: int) -> None:
        with self._sf() as s:
            g = s.get(TestGate, uid)
            if g is None:
                g = TestGate(user_id=uid, active_seconds=0)
                s.add(g)
            if g.unlocked_at is None:
                g.unlocked_at = now()
            s.commit()

    def feedback_add(self, uid: int, stars: int, insight: str) -> int:
        with self._sf() as s:
            f = Feedback(user_id=uid, stars=int(stars), insight=insight)
            s.add(f)
            s.commit()
            s.refresh(f)
            return f.id

    def feedback_list(self, limit: int = 100) -> list[dict]:
        """Admin-only: submitted test-phase feedback, newest first (capped)."""
        limit = max(1, min(int(limit), 500))
        with self._sf() as s:
            rows = s.execute(
                select(Feedback)
                .order_by(Feedback.created_at.desc())
                .limit(limit)
            ).scalars().all()
            return [
                {"id": f.id, "user_id": f.user_id, "stars": f.stars,
                 "insight": f.insight, "created_at": f.created_at.isoformat()}
                for f in rows
            ]

    # ── Generation cap ─────────────────────────────────────────────────────────

    def gen_count_today(self, uid: int, day: str) -> int:
        with self._sf() as s:
            row = s.execute(
                select(GenUsage).where(GenUsage.user_id == uid, GenUsage.day == day)
            ).scalars().first()
            return row.count if row else 0

    def gen_incr_today(self, uid: int, day: str) -> int:
        with self._sf() as s:
            row = s.execute(
                select(GenUsage).where(GenUsage.user_id == uid, GenUsage.day == day)
            ).scalars().first()
            if row is None:
                row = GenUsage(user_id=uid, day=day, count=0)
                s.add(row)
            row.count += 1
            s.commit()
            return row.count

    # ── Pool sizing ────────────────────────────────────────────────────────────

    def count_sets(self, skill: str, band: str) -> int:
        with self._sf() as s:
            return s.execute(
                select(func.count()).select_from(GeneratedSet).where(
                    GeneratedSet.skill == skill, GeneratedSet.band == band
                )
            ).scalar_one()

    def add_set(self, skill: str, band: str, payload: dict, source: str = "generated") -> int:
        """Legacy insert kept for seed/inline compatibility — hashes content and
        delegates to the Task Bank insert (dedup applies)."""
        from app.services.task_pool import content_hash as _ch
        new_id = self.add_task_bank_set(skill, band, payload, source=source,
                                        content_hash=_ch(payload))
        if new_id is None:
            # Duplicate of existing inventory: return the existing row's id.
            with self._sf() as s:
                return s.execute(
                    select(GeneratedSet.id).where(
                        GeneratedSet.skill == skill,
                        GeneratedSet.band == band,
                        GeneratedSet.content_hash == _ch(payload),
                    )
                ).scalar_one()
        return new_id

    # ── Programs & milestones ─────────────────────────────────────────────────

    def create_program(self, user_id: int, length_days: int) -> Program:
        """Insert and return the Program (with .id)."""
        with self._sf() as s:
            prog = Program(user_id=user_id, length_days=length_days)
            s.add(prog)
            s.commit()
            s.refresh(prog)
            s.expunge(prog)
        return prog

    def add_milestones(self, program_id: int, items: list[dict]) -> None:
        """Insert Milestone rows for program_id.

        Each item: {"idx", "dayTarget", "title", "targets"}.
        """
        with self._sf() as s:
            for it in items:
                s.add(
                    Milestone(
                        program_id=program_id,
                        idx=it["idx"],
                        day_target=it["dayTarget"],
                        title=it["title"],
                        targets=it["targets"],
                    )
                )
            s.commit()

    def get_milestones(self, program_id: int) -> list[dict]:
        """Return milestones ordered by idx as camelCase dicts."""
        with self._sf() as s:
            rows = (
                s.execute(
                    select(Milestone)
                    .where(Milestone.program_id == program_id)
                    .order_by(Milestone.idx)
                )
                .scalars()
                .all()
            )
            return [
                {
                    "id": r.id,
                    "idx": r.idx,
                    "dayTarget": r.day_target,
                    "title": r.title,
                    "targets": r.targets,
                }
                for r in rows
            ]

    def _owns_milestone(self, s, user_id: int, milestone_id: int):
        """Return the Milestone if it belongs to a program owned by user_id.

        WS04-05: ownership through the parent chain is enforced in the SQL
        itself (join + predicate), never by fetch-then-compare.
        """
        return s.execute(
            select(Milestone)
            .join(Program, Milestone.program_id == Program.id)
            .where(Milestone.id == milestone_id, Program.user_id == user_id)
        ).scalars().first()

    def add_milestone(self, user_id: int, title: str, day_target: int, targets: dict) -> int | None:
        """Append a milestone to the user's latest program. None if no program."""
        with self._sf() as s:
            prog = s.execute(
                select(Program).where(Program.user_id == user_id).order_by(Program.id.desc()).limit(1)
            ).scalars().first()
            if prog is None:
                return None
            next_idx = (s.execute(
                select(Milestone).where(Milestone.program_id == prog.id)
            ).scalars().all() or [])
            idx = (max((mm.idx for mm in next_idx), default=-1)) + 1
            m = Milestone(program_id=prog.id, idx=idx, day_target=day_target,
                          title=title, targets=targets or {})
            s.add(m)
            s.commit()
            s.refresh(m)
            return m.id

    def update_milestone(self, user_id: int, milestone_id: int, fields: dict) -> dict | None:
        with self._sf() as s:
            m = self._owns_milestone(s, user_id, milestone_id)
            if m is None:
                return None
            if "title" in fields and fields["title"] is not None:
                m.title = fields["title"]
            if "dayTarget" in fields and fields["dayTarget"] is not None:
                m.day_target = int(fields["dayTarget"])
            if "targets" in fields and fields["targets"] is not None:
                m.targets = fields["targets"]
            s.commit()
            s.refresh(m)
            return {"id": m.id, "idx": m.idx, "dayTarget": m.day_target,
                    "title": m.title, "targets": m.targets}

    def delete_milestone(self, user_id: int, milestone_id: int) -> bool:
        with self._sf() as s:
            m = self._owns_milestone(s, user_id, milestone_id)
            if m is None:
                return False
            s.delete(m)
            s.commit()
            return True

    # ── Attempts (Writing / Speaking history) — Phase 2c ──────────────────────

    def save_attempt(
        self,
        user_id: int,
        type: str,
        task: str,
        prompt: str,
        body: str,
        bands: dict,
        criteria: dict,
        cefr: str,
        metrics: dict,
        score_metadata: dict | None = None,
    ) -> int:
        """Insert an Attempt (writing|speaking) scoped to user_id; return its id.

        score_metadata (WS02-03) is the AI-scoring envelope persisted with the
        attempt: score_method, score_version, model_provider, model_id,
        prompt_version, rubric_version, calibration_version.
        """
        meta = score_metadata or {}
        with self._sf() as s:
            a = Attempt(
                user_id=user_id,
                type=type,
                task=task or "",
                prompt=prompt or "",
                body=body or "",
                bands=bands or {},
                criteria=criteria or {},
                cefr=cefr or "",
                metrics=metrics or {},
                score_method=meta.get("score_method"),
                score_version=meta.get("score_version"),
                model_provider=meta.get("model_provider"),
                model_id=meta.get("model_id"),
                prompt_version=meta.get("prompt_version"),
                rubric_version=meta.get("rubric_version"),
                calibration_version=meta.get("calibration_version"),
            )
            s.add(a)
            s.commit()
            s.refresh(a)
            return a.id

    def list_attempts(self, user_id: int, type: str | None = None) -> list[dict]:
        """Return this user's attempt summaries, newest first. Optional type filter."""
        with self._sf() as s:
            stmt = select(Attempt).where(Attempt.user_id == user_id).order_by(Attempt.id.desc())
            if type:
                stmt = stmt.where(Attempt.type == type)
            rows = s.execute(stmt).scalars().all()
            return [
                {
                    "id": r.id,
                    "type": r.type,
                    "task": r.task,
                    "cefr": r.cefr,
                    "overall": (r.bands or {}).get("overall") if r.type not in ("reading", "listening") and r.model_provider not in (None, "stub") else None,
                    "scoreMethod": r.score_method,
                    "modelProvider": r.model_provider,
                    "accuracyPct": (r.metrics or {}).get("accuracyPct") if r.score_method == "server_accuracy" else None,
                    "createdAt": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    def get_attempt(self, user_id: int, attempt_id: int) -> dict | None:
        """Return the full stored eval payload.

        WS04-03: the ownership predicate is part of the lookup itself, so a
        foreign attempt is indistinguishable from a missing one (no existence
        disclosure).
        """
        with self._sf() as s:
            r = s.execute(
                select(Attempt).where(
                    Attempt.id == attempt_id,
                    Attempt.user_id == user_id,
                )
            ).scalars().first()
            if r is None:
                return None
            return {
                "id": r.id,
                "type": r.type,
                "task": r.task,
                "prompt": r.prompt,
                "body": r.body,
                "bands": r.bands or {},
                "cefr": r.cefr,
                "metrics": r.metrics or {},
                "createdAt": r.created_at.isoformat() if r.created_at else None,
                # WS02-03: scoring metadata envelope (estimate transparency)
                "scoreMetadata": {
                    "scoreMethod": r.score_method,
                    "scoreVersion": r.score_version,
                    "modelProvider": r.model_provider,
                    "modelId": r.model_id,
                    "promptVersion": r.prompt_version,
                    "rubricVersion": r.rubric_version,
                    "calibrationVersion": r.calibration_version,
                },
                # flatten the stored feedback fields (corrections/rewrite/feedback/
                # modelAnswer/...) so the client renders with the same components
                **(r.criteria or {}),
            }

    def latest_skill_estimates(self, user_id: int) -> dict[str, float | None]:
        """WS20 readiness inputs: the learner's LATEST overall estimate per
        skill (None when never assessed). Ownership predicate included."""
        skills = ("listening", "reading", "writing", "speaking")
        out: dict[str, float | None] = {sk: None for sk in skills}
        with self._sf() as s:
            rows = s.execute(
                select(Attempt.type, Attempt.bands)
                .where(
                    Attempt.user_id == user_id,
                    Attempt.type.in_(("writing", "speaking")),
                    Attempt.model_provider.is_not(None),
                    Attempt.model_provider != "stub",
                )
                .order_by(Attempt.id.desc())
            ).all()
            for t, bands in rows:
                if t in out and out[t] is None:
                    ov = (bands or {}).get("overall")
                    if isinstance(ov, (int, float)):
                        out[t] = float(ov)
        return out

    def activity_stats(self, user_id: int, today) -> dict:
        """Streak + daily activity derived from this user's attempts (no extra table)."""
        from datetime import timedelta
        with self._sf() as s:
            rows = s.execute(select(Attempt).where(Attempt.user_id == user_id)).scalars().all()
            days = set()
            today_count = 0
            for r in rows:
                if not r.created_at:
                    continue
                d = self._utc_naive(r.created_at).date()
                days.add(d)
                if d == today:
                    today_count += 1
            if not days:
                return {"current": 0, "longest": 0, "today": 0, "daysActive": 0}
            # current streak: from today (or yesterday) walking back over present days
            cur = 0
            start = today if today in days else (today - timedelta(days=1) if (today - timedelta(days=1)) in days else None)
            if start is not None:
                d = start
                while d in days:
                    cur += 1
                    d = d - timedelta(days=1)
            # longest run
            longest = 0
            for d in days:
                if (d - timedelta(days=1)) not in days:  # run start
                    run, n = d, 0
                    while run in days:
                        n += 1
                        run = run + timedelta(days=1)
                    longest = max(longest, n)
            return {"current": cur, "longest": longest, "today": today_count, "daysActive": len(days)}

    def trends(self, user_id: int) -> dict:
        """This user's per-skill time series (oldest first) for the Progress chart."""
        with self._sf() as s:
            rows = s.execute(
                select(Attempt).where(Attempt.user_id == user_id).order_by(Attempt.id.asc())
            ).scalars().all()
            out: dict[str, list] = {"writing": [], "speaking": [], "reading": [], "listening": []}
            for r in rows:
                bucket = out.get(r.type) if r.type not in ("reading", "listening") and r.model_provider != "stub" else None
                if bucket is None:
                    continue
                bands = r.bands or {}
                bucket.append(
                    {
                        "id": r.id,
                        "createdAt": r.created_at.isoformat() if r.created_at else None,
                        "overall": bands.get("overall"),
                        "bands": bands,
                    }
                )
            return out

    # ── Flashcards (SM-2) — Phase 2d-4 ────────────────────────────────────────

    @staticmethod
    def _card_dict(c) -> dict:
        return {
            "id": c.id, "front": c.front, "back": c.back, "ease": c.ease,
            "interval": c.interval, "reps": c.reps, "lapses": c.lapses,
            "due": c.due.isoformat() if c.due else None,
        }

    def add_card(self, user_id: int, front: str, back: str) -> int:
        with self._sf() as s:
            c = Card(user_id=user_id, front=front, back=back)
            s.add(c)
            s.commit()
            s.refresh(c)
            return c.id

    def add_cards(self, user_id: int, items: list[dict]) -> int:
        with self._sf() as s:
            for it in items:
                s.add(Card(user_id=user_id, front=it.get("front", ""), back=it.get("back", "")))
            s.commit()
        return len(items)

    def list_cards(self, user_id: int) -> list[dict]:
        with self._sf() as s:
            rows = s.execute(
                select(Card).where(Card.user_id == user_id).order_by(Card.id.desc())
            ).scalars().all()
            return [self._card_dict(c) for c in rows]

    @staticmethod
    def _utc_naive(dt):
        """Normalise to naive-UTC so SQLite (naive) and Postgres (aware) compare."""
        if dt is None:
            return None
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    def card_stats(self, user_id: int) -> dict:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with self._sf() as s:
            rows = s.execute(select(Card).where(Card.user_id == user_id)).scalars().all()
            due = sum(1 for c in rows if c.due is None or self._utc_naive(c.due) <= now)
            return {"total": len(rows), "due": due}

    def due_cards(self, user_id: int, now) -> list[dict]:
        now_n = self._utc_naive(now)
        with self._sf() as s:
            rows = s.execute(select(Card).where(Card.user_id == user_id)).scalars().all()
            due = [c for c in rows if c.due is None or self._utc_naive(c.due) <= now_n]
            due.sort(key=lambda c: self._utc_naive(c.due) or now_n)
            return [self._card_dict(c) for c in due]

    def review_card(self, user_id: int, card_id: int, quality: int, now) -> dict | None:
        from datetime import timedelta
        from app.domain.sm2 import schedule
        with self._sf() as s:
            # WS04-03: ownership predicate inside the lookup.
            c = s.execute(
                select(Card).where(Card.id == card_id, Card.user_id == user_id)
            ).scalars().first()
            if c is None:
                return None
            nxt = schedule(c.ease, c.interval, c.reps, c.lapses, quality)
            c.ease = nxt["ease"]
            c.interval = nxt["interval"]
            c.reps = nxt["reps"]
            c.lapses = nxt["lapses"]
            c.due = now + timedelta(days=nxt["interval"])
            s.commit()
            s.refresh(c)
            return self._card_dict(c)

    def delete_card(self, user_id: int, card_id: int) -> bool:
        with self._sf() as s:
            # WS04-03: ownership predicate inside the lookup.
            c = s.execute(
                select(Card).where(Card.id == card_id, Card.user_id == user_id)
            ).scalars().first()
            if c is None:
                return False
            s.delete(c)
            s.commit()
            return True

    # ── Mock tests — Phase 2d-2 ───────────────────────────────────────────────

    def save_mock(self, user_id: int, listening: float, reading: float, overall: float) -> int:
        """Insert a Mock score scoped to user_id; return its id."""
        with self._sf() as s:
            m = Mock(user_id=user_id, listening=listening, reading=reading, overall=overall)
            s.add(m)
            s.commit()
            s.refresh(m)
            return m.id

    def list_mocks(self, user_id: int) -> list[dict]:
        """Return this user's mock scores, newest first."""
        with self._sf() as s:
            rows = s.execute(
                select(Mock).where(Mock.user_id == user_id).order_by(Mock.id.desc())
            ).scalars().all()
            return [
                {
                    "id": r.id,
                    "listening": r.listening,
                    "reading": r.reading,
                    "overall": r.overall,
                    "createdAt": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    # ── Lessons (guided sessions) — Phase 2d-1 ────────────────────────────────

    def get_lesson(self, user_id: int, day: int) -> dict | None:
        """Return this user's cached lesson for a program day, or None."""
        with self._sf() as s:
            r = s.get(Lesson, (user_id, day))
            if r is None:
                return None
            return {
                "day": r.day,
                "focus": r.focus,
                "lesson": r.lesson,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            }

    def save_lesson(self, user_id: int, day: int, lesson: dict, focus: str) -> None:
        """UPSERT a lesson by (user_id, day)."""
        with self._sf() as s:
            existing = s.get(Lesson, (user_id, day))
            if existing:
                existing.lesson = lesson
                existing.focus = focus
                existing.created_at = now()
            else:
                s.add(Lesson(user_id=user_id, day=day, lesson=lesson, focus=focus))
            s.commit()

    def get_latest_program(self, user_id: int) -> Program | None:
        """Return the most recently created Program for the user, detached, or None."""
        with self._sf() as s:
            row = (
                s.execute(
                    select(Program)
                    .where(Program.user_id == user_id)
                    .order_by(Program.id.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if row is None:
                return None
            s.refresh(row)
            s.expunge(row)
        return row

    # ── WS07: jobs ────────────────────────────────────────────────────────────

    @staticmethod
    def _job_dict(j: Job, include_result: bool = True) -> dict:
        out = {
            "id": j.id,
            "type": j.type,
            "queue": j.queue,
            "status": j.status,
            "progress": j.progress,
            "attempts": j.attempts,
            "createdAt": j.created_at.isoformat() if j.created_at else None,
            "startedAt": j.started_at.isoformat() if j.started_at else None,
            "completedAt": j.completed_at.isoformat() if j.completed_at else None,
            "expiresAt": j.expires_at.isoformat() if j.expires_at else None,
        }
        # Safe error surface only — codes and generic messages, never raw
        # provider output or stack traces.
        if j.error_code:
            out["errorCode"] = j.error_code
            out["errorMessage"] = j.error_message
        if include_result and j.status == "succeeded":
            out["result"] = j.result
        return out

    def job_create(
        self,
        job_id: str,
        job_type: str,
        queue: str,
        payload: dict,
        payload_hash: str,
        user_id: int | None = None,
        idempotency_key: str | None = None,
        expires_at=None,
    ) -> dict:
        with self._sf() as s:
            j = Job(
                id=job_id,
                user_id=user_id,
                type=job_type,
                queue=queue,
                status="queued",
                payload=payload,
                payload_hash=payload_hash,
                idempotency_key=idempotency_key,
                expires_at=self._utc_naive(expires_at) if expires_at else None,
            )
            s.add(j)
            s.commit()
            s.refresh(j)
            return self._job_dict(j)

    def job_get(self, job_id: str, user_id: int | None = None) -> dict | None:
        """Fetch a job. When user_id is given the lookup is ownership-scoped:
        another user's job (or a system job) simply does not exist for them."""
        with self._sf() as s:
            q = select(Job).where(Job.id == job_id)
            if user_id is not None:
                q = q.where(Job.user_id == user_id)
            j = s.execute(q).scalars().first()
            if j is None:
                return None
            out = self._job_dict(j)
            out["payloadHash"] = j.payload_hash
            out["payload"] = j.payload
            out["provider"] = j.provider
            out["modelRequested"] = j.model_requested
            out["modelUsed"] = j.model_used
            return out

    def job_by_idempotency(self, user_id: int | None, key: str) -> dict | None:
        with self._sf() as s:
            q = select(Job).where(Job.idempotency_key == key)
            q = q.where(
                Job.user_id.is_(None) if user_id is None else Job.user_id == user_id
            )
            j = s.execute(q).scalars().first()
            if j is None:
                return None
            out = self._job_dict(j)
            out["payloadHash"] = j.payload_hash
            return out

    def job_set_running(self, job_id: str) -> None:
        with self._sf() as s:
            j = s.get(Job, job_id)
            if j is not None and j.status == "queued":
                j.status = "running"
                j.started_at = now()
                j.attempts = (j.attempts or 0) + 1
                s.commit()

    def job_set_succeeded(
        self,
        job_id: str,
        result: dict,
        provider: str | None = None,
        model_requested: str | None = None,
        model_used: str | None = None,
    ) -> None:
        with self._sf() as s:
            j = s.get(Job, job_id)
            if j is not None:
                j.status = "succeeded"
                j.result = result
                j.completed_at = now()
                if provider:
                    j.provider = provider
                if model_requested:
                    j.model_requested = model_requested
                if model_used:
                    j.model_used = model_used
                s.commit()

    def job_fail(
        self,
        job_id: str,
        code: str,
        message: str,
        provider: str | None = None,
        model_requested: str | None = None,
        model_used: str | None = None,
    ) -> None:
        with self._sf() as s:
            j = s.get(Job, job_id)
            if j is not None:
                j.status = "failed"
                j.error_code = code[:40]
                j.error_message = message[:200]
                j.completed_at = now()
                if provider:
                    j.provider = provider
                if model_requested:
                    j.model_requested = model_requested
                if model_used:
                    j.model_used = model_used
                s.commit()

    def job_cancel(self, job_id: str, code: str, message: str) -> None:
        with self._sf() as s:
            j = s.get(Job, job_id)
            if j is not None:
                j.status = "cancelled"
                j.error_code = code[:40]
                j.error_message = message[:200]
                j.completed_at = now()
                s.commit()

    def jobs_purge_expired(self, before) -> int:
        """Delete finished jobs whose retention window passed. Returns count."""
        with self._sf() as s:
            rows = s.execute(
                select(Job).where(
                    Job.expires_at.is_not(None),
                    Job.expires_at < self._utc_naive(before),
                    Job.status.in_(["succeeded", "failed", "cancelled", "expired"]),
                )
            ).scalars().all()
            n = len(rows)
            for j in rows:
                s.delete(j)
            s.commit()
            return n

    # ── WS07: append-only AI usage ledger ─────────────────────────────────────

    def ledger_add(
        self,
        cost_center: str,
        op: str,
        user_id: int | None = None,
        skill: str | None = None,
        band: str | None = None,
        provider: str | None = None,
        model_requested: str | None = None,
        model_used: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        reasoning_tokens: int | None = None,
        cached_tokens: int | None = None,
        cost_micros: int | None = None,
        cost_source: str | None = None,
        status: str = "ok",
        error_code: str | None = None,
        cache_hit: bool = False,
        job_id: str | None = None,
    ) -> int:
        """Append one usage record. There is deliberately no update/delete
        path — the ledger is append-only (WS07-08)."""
        with self._sf() as s:
            row = AiUsageLedger(
                user_id=user_id,
                cost_center=cost_center,
                op=op,
                skill=skill,
                band=band,
                provider=provider,
                model_requested=model_requested,
                model_used=model_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                reasoning_tokens=reasoning_tokens,
                cached_tokens=cached_tokens,
                cost_micros=cost_micros,
                cost_source=cost_source,
                status=status,
                error_code=error_code,
                cache_hit=cache_hit,
                job_id=job_id,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return row.id

    def ledger_sum_cost(self, start, end, cost_center: str | None = None) -> int:
        """Sum cost_micros over [start, end). start/end are UTC datetimes."""
        with self._sf() as s:
            q = select(func.coalesce(func.sum(AiUsageLedger.cost_micros), 0)).where(
                AiUsageLedger.created_at >= self._utc_naive(start),
                AiUsageLedger.created_at < self._utc_naive(end),
            )
            if cost_center is not None:
                q = q.where(AiUsageLedger.cost_center == cost_center)
            return int(s.execute(q).scalar_one() or 0)

    def ledger_count_ops(self, start, end, cost_center: str, status: str = "ok") -> int:
        with self._sf() as s:
            return int(s.execute(
                select(func.count(AiUsageLedger.id)).where(
                    AiUsageLedger.created_at >= self._utc_naive(start),
                    AiUsageLedger.created_at < self._utc_naive(end),
                    AiUsageLedger.cost_center == cost_center,
                    AiUsageLedger.status == status,
                )
            ).scalar_one() or 0)

    # ── WS07: system flags ────────────────────────────────────────────────────

    def flag_get(self, key: str) -> str | None:
        with self._sf() as s:
            row = s.get(SystemFlag, key)
            return row.value if row is not None else None

    def flag_set(self, key: str, value: str) -> None:
        with self._sf() as s:
            row = s.get(SystemFlag, key)
            if row is None:
                s.add(SystemFlag(key=key, value=str(value)))
            else:
                row.value = str(value)
                row.updated_at = now()
            s.commit()

    # ── Product analytics (WS21) — append-only, content-free ──────────────────

    def save_analytics_event(self, envelope: dict) -> bool:
        """Persist a validated analytics envelope.

        Idempotent on event_id (client retries dedupe on the PK). Returns
        False when the event_id was already stored. Never raises on conflict.
        """
        with self._sf() as s:
            if s.get(AnalyticsEvent, envelope["event_id"]) is not None:
                return False
            s.add(
                AnalyticsEvent(
                    event_id=envelope["event_id"],
                    user_id=envelope.get("user_id"),
                    name=envelope["event_name"],
                    event_version=envelope.get("event_version", 1),
                    occurred_at=datetime.fromisoformat(envelope["occurred_at"]),
                    cohort_id=envelope.get("cohort_id"),
                    acquisition_source=envelope.get("acquisition_source"),
                    anonymous_id=envelope.get("anonymous_id"),
                    properties=envelope.get("properties") or {},
                )
            )
            s.commit()
            return True

    def set_acquisition(self, user_id: int, acquisition_source: str | None,
                        cohort_id: str | None) -> None:
        """Attach server-validated acquisition/cohort dimensions (once)."""
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            if u is None:
                return
            if acquisition_source:
                u.acquisition_source = acquisition_source
            if cohort_id:
                u.cohort_id = cohort_id
            s.commit()

    def _analytics_rows(self, s, *, user_ids=None, names=None, since=None, until=None):
        stmt = select(
            AnalyticsEvent.user_id,
            AnalyticsEvent.name,
            AnalyticsEvent.occurred_at,
            AnalyticsEvent.cohort_id,
        )
        if user_ids is not None:
            stmt = stmt.where(AnalyticsEvent.user_id.in_(user_ids))
        if names:
            stmt = stmt.where(AnalyticsEvent.name.in_(names))
        if since is not None:
            stmt = stmt.where(AnalyticsEvent.occurred_at >= since)
        if until is not None:
            stmt = stmt.where(AnalyticsEvent.occurred_at <= until)
        return s.execute(stmt).all()

    def weekly_meaningful_learners(self, *, as_of) -> int:
        """WML: distinct users with >=1 qualifying action in the rolling 7d
        window ending at as_of. Computation lives in domain.analytics so it is
        reproducible independent of storage."""
        from app.domain.analytics import WML_QUALIFYING_EVENTS, weekly_meaningful_learners
        with self._sf() as s:
            rows = self._analytics_rows(s, names=sorted(WML_QUALIFYING_EVENTS))
        return weekly_meaningful_learners(
            [(r.user_id, r.name, r.occurred_at) for r in rows],
            as_of=as_of,
        )

    def analytics_counts(self, *, since=None) -> dict[str, int]:
        """Total stored events per name (server-authoritative funnel counts)."""
        with self._sf() as s:
            stmt = select(AnalyticsEvent.name, func.count()).group_by(AnalyticsEvent.name)
            if since is not None:
                stmt = stmt.where(AnalyticsEvent.occurred_at >= since)
            rows = s.execute(stmt).all()
        return {name: int(n) for name, n in rows}

    def analytics_by_cohort(self, *, names=None) -> list[dict]:
        """Per-cohort breakdown — cohorts are NEVER merged in one number.

        Returns one row per (cohort_id, acquisition_source) with event counts
        and distinct active users, so lecturer-controlled and voluntary
        cohorts are always comparable side-by-side.
        """
        with self._sf() as s:
            stmt = select(
                AnalyticsEvent.cohort_id,
                AnalyticsEvent.acquisition_source,
                AnalyticsEvent.name,
                AnalyticsEvent.user_id,
            )
            if names:
                stmt = stmt.where(AnalyticsEvent.name.in_(names))
            rows = s.execute(stmt).all()
        agg: dict[tuple, dict] = {}
        seen_users: dict[tuple, set] = {}
        for cohort_id, source, name, user_id in rows:
            key = (cohort_id, source)
            agg.setdefault(key, {"events": 0})
            agg[key]["events"] += 1
            if user_id is not None:
                seen_users.setdefault(key, set()).add(user_id)
        return [
            {
                "cohortId": k[0],
                "acquisitionSource": k[1],
                "events": v["events"],
                "distinctUsers": len(seen_users.get(k, set())),
            }
            for k, v in sorted(agg.items(), key=lambda kv: (kv[0][0] or "", kv[0][1] or ""))
        ]

    def purge_old_analytics_events(self, *, older_than) -> int:
        """Retention hook: delete raw events older than the cutoff datetime.

        Aggregates derived before deletion stay authoritative for WML windows
        (rolling 7d << 180d retention), so purging never changes WML math.
        """
        with self._sf() as s:
            n = s.execute(
                sa_delete(AnalyticsEvent).where(AnalyticsEvent.occurred_at < older_than)
            ).rowcount or 0
            s.commit()
            return int(n)

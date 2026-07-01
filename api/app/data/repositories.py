"""Repository facade — Data layer only.

All methods open a short-lived session via self._sf(), commit writes,
and return plain dicts or detached ORM objects.  No business logic here.
"""

import random
from datetime import datetime, timezone

from sqlalchemy import func, select

from .models import (
    Attempt,
    Card,
    GeneratedSet,
    Lesson,
    Milestone,
    Mock,
    PlacementAttempt,
    PlacementCombo,
    PlacementItem,
    Program,
    SkillLevel,
    UserProfile,
    now,
)


class Repository:
    def __init__(self, session_factory):
        self._sf = session_factory

    # ── User ──────────────────────────────────────────────────────────────────

    def create_user(
        self,
        name: str,
        goal: str,
        target_band: float,
        skill_targets: dict,
    ) -> UserProfile:
        """Insert a new UserProfile and return the detached object (with .id)."""
        with self._sf() as s:
            u = UserProfile(
                name=name,
                goal=goal,
                target_band=target_band,
                skill_targets=skill_targets,
            )
            s.add(u)
            s.commit()
            s.refresh(u)
            s.expunge(u)
        return u

    # ── Accounts (Phase 3a) ───────────────────────────────────────────────────

    def create_account(self, email, password, name="", goal="other", target_band=6.0,
                       skill_targets=None) -> UserProfile:
        from werkzeug.security import generate_password_hash
        with self._sf() as s:
            u = UserProfile(
                name=name, goal=goal, target_band=target_band,
                skill_targets=skill_targets or {},
                email=email, password_hash=generate_password_hash(password),
            )
            s.add(u)
            s.commit()
            s.refresh(u)
            s.expunge(u)
        return u

    def attach_credentials(self, user_id, email, password) -> UserProfile:
        from werkzeug.security import generate_password_hash
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            u.email = email
            u.password_hash = generate_password_hash(password)
            s.commit()
            s.refresh(u)
            s.expunge(u)
        return u

    def upsert_google_user(self, sub: str, email: str = "", name: str = "") -> UserProfile:
        """Find a user by google_sub; else link to an existing same-email account;
        else create a new (password-less) account. Returns the detached user."""
        with self._sf() as s:
            row = s.execute(
                select(UserProfile).where(UserProfile.google_sub == sub)
            ).scalars().first()
            if row is None and email:
                row = s.execute(
                    select(UserProfile).where(UserProfile.email == email)
                ).scalars().first()
                if row is not None:
                    row.google_sub = sub  # link Google to the existing email account
            if row is None:
                row = UserProfile(
                    name=name or "", goal="other", target_band=6.0, skill_targets={},
                    email=email or None, google_sub=sub,
                )
                s.add(row)
            elif name and not row.name:
                row.name = name
            s.commit()
            s.refresh(row)
            s.expunge(row)
        return row

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
        from werkzeug.security import check_password_hash
        u = self.get_account_by_email(email)
        if u is None or not u.password_hash or not check_password_hash(u.password_hash, password):
            return None
        return u

    def set_password(self, user_id, password) -> None:
        from werkzeug.security import generate_password_hash
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            u.password_hash = generate_password_hash(password)
            s.commit()

    def change_password(self, user_id, current, new) -> bool:
        """Verify `current` then set `new`. False if current is wrong."""
        from werkzeug.security import check_password_hash, generate_password_hash
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            if u is None or not u.password_hash or not check_password_hash(u.password_hash, current):
                return False
            u.password_hash = generate_password_hash(new)
            s.commit()
            return True

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
        """All of this user's data as plain JSON-able dicts (data portability)."""
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            profile = {"id": u.id, "email": u.email, "name": u.name, "goal": u.goal,
                       "targetBand": u.target_band, "skillTargets": u.skill_targets,
                       "country": u.country, "examDate": u.exam_date, "bio": u.bio} if u else {}
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
                "skillLevels": dump(SkillLevel, user_id=user_id),
                "attempts": dump(Attempt, user_id=user_id),
                "mocks": dump(Mock, user_id=user_id),
                "cards": dump(Card, user_id=user_id),
                "lessons": dump(Lesson, user_id=user_id),
                "programs": programs,
                "milestones": milestones,
                "placementAttempts": dump(PlacementAttempt, user_id=user_id),
            }

    def delete_account(self, user_id) -> bool:
        """Delete the user and every row they own. Idempotent-ish (False if absent)."""
        with self._sf() as s:
            u = s.get(UserProfile, user_id)
            if u is None:
                return False
            # child rows first
            for model in (Attempt, Mock, Card, Lesson, SkillLevel, PlacementAttempt):
                for r in s.execute(select(model).where(model.user_id == user_id)).scalars().all():
                    s.delete(r)
            for p in s.execute(select(Program).where(Program.user_id == user_id)).scalars().all():
                for m in s.execute(select(Milestone).where(Milestone.program_id == p.id)).scalars().all():
                    s.delete(m)
                s.delete(p)
            s.delete(u)
            s.commit()
            return True

    # ── Admin (Manage users) ──────────────────────────────────────────────────

    def list_accounts(self) -> list[dict]:
        """Every registered account (email not null), oldest first, with usage counts."""
        with self._sf() as s:
            users = s.execute(
                select(UserProfile)
                .where(UserProfile.email.is_not(None))
                .order_by(UserProfile.id)
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
        """Return ONE random GeneratedSet.payload for (skill, band), or None."""
        with self._sf() as s:
            rows = (
                s.execute(
                    select(GeneratedSet).where(
                        GeneratedSet.skill == skill,
                        GeneratedSet.band == band,
                    )
                )
                .scalars()
                .all()
            )
            if not rows:
                return None
            return random.choice(rows).payload

    def serve_any_set(self, skill: str) -> dict | None:
        """Return ONE random GeneratedSet.payload for the skill (any band), or None."""
        with self._sf() as s:
            rows = (
                s.execute(
                    select(GeneratedSet).where(
                        GeneratedSet.skill == skill,
                    )
                )
                .scalars()
                .all()
            )
            if not rows:
                return None
            return random.choice(rows).payload

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
        """Return the Milestone if it belongs to a program owned by user_id, else None."""
        m = s.get(Milestone, milestone_id)
        if m is None:
            return None
        prog = s.get(Program, m.program_id)
        if prog is None or prog.user_id != user_id:
            return None
        return m

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
    ) -> int:
        """Insert an Attempt (writing|speaking) scoped to user_id; return its id."""
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
                    "overall": (r.bands or {}).get("overall"),
                    "createdAt": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    def get_attempt(self, user_id: int, attempt_id: int) -> dict | None:
        """Return the full stored eval payload — only if it belongs to user_id."""
        with self._sf() as s:
            r = s.get(Attempt, attempt_id)
            if r is None or r.user_id != user_id:
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
                # flatten the stored feedback fields (corrections/rewrite/feedback/
                # modelAnswer/...) so the client renders with the same components
                **(r.criteria or {}),
            }

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
                bucket = out.get(r.type)
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
            c = s.get(Card, card_id)
            if c is None or c.user_id != user_id:
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
            c = s.get(Card, card_id)
            if c is None or c.user_id != user_id:
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

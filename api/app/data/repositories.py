"""Repository facade — Data layer only.

All methods open a short-lived session via self._sf(), commit writes,
and return plain dicts or detached ORM objects.  No business logic here.
"""

import random
from datetime import datetime, timezone

from sqlalchemy import select

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
                    "idx": r.idx,
                    "dayTarget": r.day_target,
                    "title": r.title,
                    "targets": r.targets,
                }
                for r in rows
            ]

    # ── Attempts (Writing / Speaking history) — Phase 2c ──────────────────────

    def save_attempt(
        self,
        type: str,
        task: str,
        prompt: str,
        body: str,
        bands: dict,
        criteria: dict,
        cefr: str,
        metrics: dict,
    ) -> int:
        """Insert an Attempt (writing|speaking) and return its id."""
        with self._sf() as s:
            a = Attempt(
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

    def list_attempts(self, type: str | None = None) -> list[dict]:
        """Return attempt summaries, newest first. Optionally filter by type."""
        with self._sf() as s:
            stmt = select(Attempt).order_by(Attempt.id.desc())
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

    def get_attempt(self, attempt_id: int) -> dict | None:
        """Return the full stored eval payload (re-renderable), or None."""
        with self._sf() as s:
            r = s.get(Attempt, attempt_id)
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
                # flatten the stored feedback fields (corrections/rewrite/feedback/
                # modelAnswer/...) so the client renders with the same components
                **(r.criteria or {}),
            }

    def trends(self) -> dict:
        """Per-skill time series (oldest first) for the Progress chart."""
        with self._sf() as s:
            rows = s.execute(select(Attempt).order_by(Attempt.id.asc())).scalars().all()
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

    def add_card(self, front: str, back: str) -> int:
        with self._sf() as s:
            c = Card(front=front, back=back)
            s.add(c)
            s.commit()
            s.refresh(c)
            return c.id

    def add_cards(self, items: list[dict]) -> int:
        with self._sf() as s:
            for it in items:
                s.add(Card(front=it.get("front", ""), back=it.get("back", "")))
            s.commit()
        return len(items)

    def list_cards(self) -> list[dict]:
        with self._sf() as s:
            rows = s.execute(select(Card).order_by(Card.id.desc())).scalars().all()
            return [self._card_dict(c) for c in rows]

    @staticmethod
    def _utc_naive(dt):
        """Normalise to naive-UTC so SQLite (naive) and Postgres (aware) compare."""
        if dt is None:
            return None
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    def card_stats(self) -> dict:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with self._sf() as s:
            rows = s.execute(select(Card)).scalars().all()
            due = sum(1 for c in rows if c.due is None or self._utc_naive(c.due) <= now)
            return {"total": len(rows), "due": due}

    def due_cards(self, now) -> list[dict]:
        now_n = self._utc_naive(now)
        with self._sf() as s:
            rows = s.execute(select(Card)).scalars().all()
            due = [c for c in rows if c.due is None or self._utc_naive(c.due) <= now_n]
            due.sort(key=lambda c: self._utc_naive(c.due) or now_n)
            return [self._card_dict(c) for c in due]

    def review_card(self, card_id: int, quality: int, now) -> dict | None:
        from datetime import timedelta
        from app.domain.sm2 import schedule
        with self._sf() as s:
            c = s.get(Card, card_id)
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

    def delete_card(self, card_id: int) -> bool:
        with self._sf() as s:
            c = s.get(Card, card_id)
            if c is None:
                return False
            s.delete(c)
            s.commit()
            return True

    # ── Mock tests — Phase 2d-2 ───────────────────────────────────────────────

    def save_mock(self, listening: float, reading: float, overall: float) -> int:
        """Insert a Mock score and return its id."""
        with self._sf() as s:
            m = Mock(listening=listening, reading=reading, overall=overall)
            s.add(m)
            s.commit()
            s.refresh(m)
            return m.id

    def list_mocks(self) -> list[dict]:
        """Return mock scores, newest first."""
        with self._sf() as s:
            rows = s.execute(select(Mock).order_by(Mock.id.desc())).scalars().all()
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

    def get_lesson(self, day: int) -> dict | None:
        """Return the cached lesson for a program day, or None."""
        with self._sf() as s:
            r = s.get(Lesson, day)
            if r is None:
                return None
            return {
                "day": r.day,
                "focus": r.focus,
                "lesson": r.lesson,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            }

    def save_lesson(self, day: int, lesson: dict, focus: str) -> None:
        """UPSERT a lesson by day (PK)."""
        with self._sf() as s:
            existing = s.get(Lesson, day)
            if existing:
                existing.lesson = lesson
                existing.focus = focus
                existing.created_at = now()
            else:
                s.add(Lesson(day=day, lesson=lesson, focus=focus))
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

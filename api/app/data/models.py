from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def now():
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class UserProfile(Base):
    __tablename__ = "user_profile"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    goal: Mapped[str] = mapped_column(String(20))
    target_band: Mapped[float] = mapped_column(Float)
    skill_targets: Mapped[dict] = mapped_column(JSON, default=dict)
    # Phase 3a — account identity (nullable: a profile may start anonymous).
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)  # reserved for OAuth
    # Phase 3e — profile detail + avatar (base64 data URL).
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    exam_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ISO yyyy-mm-dd
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar: Mapped[str | None] = mapped_column(String, nullable=True)
    # Phase 4a — study reminder ("HH:MM" local hour, or null = off) + last-sent date.
    reminder_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    reminder_last_sent: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Per-user IANA timezone (e.g. "Asia/Jakarta") the reminder hour is local to.
    reminder_tz: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class SkillLevel(Base):
    __tablename__ = "skill_levels"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"))
    skill: Mapped[str] = mapped_column(String(20))
    band: Mapped[str] = mapped_column(String(6))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class PlacementCombo(Base):
    __tablename__ = "placement_combos"
    combo_id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    target_minutes: Mapped[int] = mapped_column(Integer, default=50)
    sections: Mapped[dict] = mapped_column(JSON)

class PlacementItem(Base):
    __tablename__ = "placement_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    combo_id: Mapped[int] = mapped_column(ForeignKey("placement_combos.combo_id"))
    skill: Mapped[str] = mapped_column(String(20))
    band_tag: Mapped[str] = mapped_column(String(6))
    type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    section_seconds: Mapped[int] = mapped_column(Integer, default=0)

class PlacementAttempt(Base):
    __tablename__ = "placement_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"))
    combo_id: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    per_skill: Mapped[dict] = mapped_column(JSON)
    overall_band: Mapped[float] = mapped_column(Float)
    cefr: Mapped[str] = mapped_column(String(6))
    gap_to_target: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class GeneratedSet(Base):
    __tablename__ = "generated_sets"
    id: Mapped[int] = mapped_column(primary_key=True)
    skill: Mapped[str] = mapped_column(String(20))
    band: Mapped[str] = mapped_column(String(6))
    set_index: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(12), default="seed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class TestGate(Base):
    __tablename__ = "test_gate"
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), primary_key=True)
    active_seconds: Mapped[int] = mapped_column(Integer, default=0)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"))
    stars: Mapped[int] = mapped_column(Integer)
    insight: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class GenUsage(Base):
    __tablename__ = "gen_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"))
    day: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD (UTC)
    count: Mapped[int] = mapped_column(Integer, default=0)

class Program(Base):
    __tablename__ = "programs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"))
    length_days: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    status: Mapped[str] = mapped_column(String(12), default="active")

class Milestone(Base):
    __tablename__ = "milestones"
    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"))
    idx: Mapped[int] = mapped_column(Integer)
    day_target: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(160))
    targets: Mapped[dict] = mapped_column(JSON)
    achieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user_profile.id"), index=True, nullable=True)
    type: Mapped[str] = mapped_column(String(20))
    task: Mapped[str] = mapped_column(String(40), default="")
    prompt: Mapped[str] = mapped_column(String, default="")
    body: Mapped[str] = mapped_column(String, default="")
    bands: Mapped[dict] = mapped_column(JSON, default=dict)
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    cefr: Mapped[str] = mapped_column(String(6), default="")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Mock(Base):
    __tablename__ = "mocks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user_profile.id"), index=True, nullable=True)
    listening: Mapped[float] = mapped_column(Float, default=0.0)
    reading: Mapped[float] = mapped_column(Float, default=0.0)
    overall: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Lesson(Base):
    __tablename__ = "lessons"
    # Per-user lessons: composite PK (user_id, day). user_id NULLable for the
    # anonymous case is avoided — lessons are always tied to a session user.
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), primary_key=True)
    day: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson: Mapped[dict] = mapped_column(JSON)
    focus: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Card(Base):
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user_profile.id"), index=True, nullable=True)
    front: Mapped[str] = mapped_column(String)
    back: Mapped[str] = mapped_column(String)
    ease: Mapped[float] = mapped_column(Float, default=2.5)
    interval: Mapped[int] = mapped_column(Integer, default=0)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    due: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

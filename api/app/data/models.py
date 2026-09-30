from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    DateTime,
    JSON,
    Index,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(timezone.utc)


@event.listens_for(Engine, "connect")
def _sqlite_enable_foreign_keys(dbapi_connection, connection_record):
    """WS04-04: make SQLite dev/test behave like PostgreSQL prod.

    SQLite ships with referential integrity OFF per connection; every other
    dialect enforces FKs. Turning it on here means ON DELETE CASCADE rules in
    the schema (and the tests that rely on them) behave the same everywhere.
    """
    if dbapi_connection.__class__.__module__.split(".")[0] == "sqlite3":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


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
    # WS03-05 — email ownership verified? Google-verified emails adopt True;
    # local registrations start False until the one-time verify token is used.
    email_verified: Mapped[bool] = mapped_column(default=False)
    # WS21 — acquisition/cohort dimensions. Server-owned and validated against
    # app.domain.analytics allow-lists; never client-declared free text.
    acquisition_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cohort_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuthSession(Base):
    """WS03-01 — server-side session state.

    The browser holds only an opaque random token (cookie ``ar_sid``); this row
    is the authoritative state and is the ONLY thing that can be revoked.
    ``id`` is sha256(token) so a DB leak cannot mint cookies. Deleted with the
    account (ON DELETE CASCADE); revoked rows are retained briefly for audit
    and purged by maintenance.
    """

    __tablename__ = "auth_session"
    __table_args__ = (
        Index("ix_auth_session_user", "user_id"),
        Index("ix_auth_session_revoked", "revoked_at"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256(token) hex
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=True
    )
    # Double-submit CSRF token for this session (also set as a JS-readable cookie).
    csrf_token: Mapped[str] = mapped_column(String(64))
    # Small non-identity payload: {"gate": true} for the passcode gate,
    # {"reauth_at": iso} for admin reauthentication. No learner content here.
    flags: Mapped[dict] = mapped_column(JSON, default=dict)
    remember: Mapped[bool] = mapped_column(default=False)
    device: Mapped[str] = mapped_column(String(200), default="")  # truncated User-Agent
    ip_hash: Mapped[str] = mapped_column(String(64), default="")  # sha256(ip) — no raw IP
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuthOneTimeToken(Base):
    """WS03-05/06 — single-use expiring tokens (password reset, email verify).

    Only sha256(token) is stored; the raw token exists solely in the emailed
    link. ``used_at`` makes consumption one-time; successful password reset
    invalidates every outstanding token for the user.
    """

    __tablename__ = "auth_one_time_token"
    __table_args__ = (
        Index("ix_ott_user", "user_id"),
        Index("ix_ott_token_hash", "token_hash", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # "reset" | "verify"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Security-audit metadata — never the token itself.
    request_ip_hash: Mapped[str] = mapped_column(String(64), default="")
    request_ua: Mapped[str] = mapped_column(String(200), default="")


class AdminAudit(Base):
    """WS03-07 — append-only audit trail for privileged actions.

    Deliberately NOT user-owned: audit rows must survive the deletion of the
    actor (actor_user_id is SET NULL; actor_email/denormalised target kept as
    plain columns). Retention: reviewed at each release; rows contain no
    learner content — actor/target ids, action kind, hashed IP, timestamp.
    """

    __tablename__ = "admin_audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_profile.id", ondelete="SET NULL"), nullable=True
    )
    actor_email: Mapped[str] = mapped_column(String(255), default="")
    action: Mapped[str] = mapped_column(String(64))  # login / delete_user / reset_user_password
    target_user_id: Mapped[int | None] = mapped_column(nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class SkillLevel(Base):
    __tablename__ = "skill_levels"
    __table_args__ = (Index("ix_skill_levels_user", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    # WS04-04: user-owned row; deleted with the account (ON DELETE CASCADE).
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE")
    )
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
    __table_args__ = (Index("ix_placement_attempts_user", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE")
    )
    combo_id: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    per_skill: Mapped[dict] = mapped_column(JSON)
    overall_band: Mapped[float] = mapped_column(Float)
    cefr: Mapped[str] = mapped_column(String(6))
    gap_to_target: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class GeneratedSet(Base):
    """WS27: evolved into shared Task Bank semantics (per skill/band bucket).

    Lifecycle: generated content is validated + deduplicated BEFORE it becomes
    ``active``; quarantined/retired rows are never served. Existing rows (seed
    inventory) default to active. ``content_hash`` backs exact-duplicate
    rejection; ``generation_meta`` carries model/provider/prompt provenance
    and ``gen_cost_micros`` the amortization input — none of this is exposed
    to learner API responses.
    """
    __tablename__ = "generated_sets"
    __table_args__ = (
        Index("ix_sets_bucket_status", "skill", "band", "status"),
        # Exact-duplicate rejection (NULL hashes — legacy rows — never clash).
        Index("ix_sets_bucket_hash", "skill", "band", "content_hash", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    skill: Mapped[str] = mapped_column(String(20))
    band: Mapped[str] = mapped_column(String(6))
    set_index: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(12), default="seed")
    # WS27 lifecycle: active | quarantined | retired (serving filters on this)
    status: Mapped[str] = mapped_column(String(12), default="active")
    pool_kind: Mapped[str] = mapped_column(String(20), default="practice_adaptive")
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quality_flags: Mapped[dict] = mapped_column(JSON, default=dict)
    generation_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    gen_cost_micros: Mapped[int | None] = mapped_column(Integer, nullable=True)
    serve_count: Mapped[int] = mapped_column(Integer, default=0)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TaskExposure(Base):
    """WS27: per-user task exposure history.

    Powers anti-repeat selection (never serve what the user just saw) and the
    repeat-rate metric. Rows contain NO learner content — ids, timestamps and
    a small selection-context tag only. Deleted with the account (CASCADE)
    and when a set row is removed (CASCADE through generated_sets).
    """
    __tablename__ = "task_exposure"
    __table_args__ = (
        Index("ix_exposure_user_set_time", "user_id", "set_id", "served_at"),
        Index("ix_exposure_set_time", "set_id", "served_at"),
        Index("ix_exposure_user_time", "user_id", "served_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE")
    )
    set_id: Mapped[int] = mapped_column(
        ForeignKey("generated_sets.id", ondelete="CASCADE")
    )
    served_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # "practice" | "fallback_adjacent" — why this item was chosen.
    selection_context: Mapped[str] = mapped_column(String(20), default="practice")
    repeat: Mapped[bool] = mapped_column(Boolean, default=False)

class TestGate(Base):
    __tablename__ = "test_gate"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE"), primary_key=True
    )
    active_seconds: Mapped[int] = mapped_column(Integer, default=0)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (Index("ix_feedback_user", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE")
    )
    stars: Mapped[int] = mapped_column(Integer)
    insight: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class GenUsage(Base):
    __tablename__ = "gen_usage"
    __table_args__ = (Index("ix_gen_usage_user_day", "user_id", "day", unique=True),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE")
    )
    day: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD (UTC)
    count: Mapped[int] = mapped_column(Integer, default=0)

class Program(Base):
    __tablename__ = "programs"
    __table_args__ = (Index("ix_programs_user", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE")
    )
    length_days: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    status: Mapped[str] = mapped_column(String(12), default="active")

class Milestone(Base):
    __tablename__ = "milestones"
    # Owned through Program (WS04-05): cascading from program cascades here too.
    __table_args__ = (Index("ix_milestones_program", "program_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE")
    )
    idx: Mapped[int] = mapped_column(Integer)
    day_target: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(160))
    targets: Mapped[dict] = mapped_column(JSON)
    achieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    # WS04-02: persistent learner history always belongs to a session user.
    # (index=True keeps the original ix_attempts_user_id created by the schema.)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(20))
    task: Mapped[str] = mapped_column(String(40), default="")
    prompt: Mapped[str] = mapped_column(String, default="")
    body: Mapped[str] = mapped_column(String, default="")
    bands: Mapped[dict] = mapped_column(JSON, default=dict)
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    cefr: Mapped[str] = mapped_column(String(6), default="")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    # WS02-03: Scoring metadata envelope for AI-scored attempts
    score_method: Mapped[str | None] = mapped_column(String(20), nullable=True)  # deterministic, llm_estimate, audio_estimate
    score_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    model_provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rubric_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    calibration_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Mock(Base):
    __tablename__ = "mocks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE"), index=True
    )
    listening: Mapped[float] = mapped_column(Float, default=0.0)
    reading: Mapped[float] = mapped_column(Float, default=0.0)
    overall: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Lesson(Base):
    __tablename__ = "lessons"
    # Per-user lessons: composite PK (user_id, day) already scopes every lookup.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson: Mapped[dict] = mapped_column(JSON)
    focus: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Card(Base):
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE"), index=True
    )
    front: Mapped[str] = mapped_column(String)
    back: Mapped[str] = mapped_column(String)
    ease: Mapped[float] = mapped_column(Float, default=2.5)
    interval: Mapped[int] = mapped_column(Integer, default=0)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    due: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ── WS07: jobs, AI usage ledger, system flags ────────────────────────────────

class Job(Base):
    """Persistent job record for heavy/queued work (WS07-03).

    ``id`` is an unguessable UUID, so status lookups are not enumerable even
    before the user check. Status lookup is ALWAYS user-scoped: system jobs
    (user_id NULL, e.g. pool replenishment) are never exposed via the API.
    """
    __tablename__ = "jobs"
    __table_args__ = (
        # Idempotency binding (WS07-05). The key embeds the owner
        # ("...:u:<id|sys>:<key>") so a SINGLE unique index covers both user
        # jobs and system jobs (NULL user_id rows are DISTINCT in SQL unique
        # indexes — a composite (user_id, key) index would not dedupe them).
        Index("ix_jobs_idem", "idempotency_key", unique=True),
        Index("ix_jobs_user_created", "user_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(40))
    queue: Mapped[str] = mapped_column(String(20), default="default")
    status: Mapped[str] = mapped_column(String(12), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    payload_hash: Mapped[str] = mapped_column(String(64), default="")
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # SAFE error surface only: a short code + generic message. Never the raw
    # provider error, stack trace, or key material (WS07 required test).
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(200), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model_requested: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(80), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AiUsageLedger(Base):
    """Append-only provider-usage/cost ledger (WS07-08; WS27 extends this).

    The single source of truth for AI spend accounting. No code path updates
    or deletes rows; retention is an ops decision, not an app behaviour. It
    stores ONLY accounting metadata — never learner essays, transcripts, or
    prompts. ``user_id`` is SET NULL on account deletion: the cost record
    survives (financial record) but loses its personal identifier.
    """
    __tablename__ = "ai_usage_ledger"
    __table_args__ = (
        Index("ix_ledger_user_created", "user_id", "created_at"),
        Index("ix_ledger_center_created", "cost_center", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_profile.id", ondelete="SET NULL"), nullable=True
    )
    # system/background vs learner-attributed cost centres:
    # pool_replenish | learner_scoring | learner_generation | aura | asr | ...
    cost_center: Mapped[str] = mapped_column(String(40))
    op: Mapped[str] = mapped_column(String(40))          # score|generate|...
    skill: Mapped[str | None] = mapped_column(String(20), nullable=True)
    band: Mapped[str | None] = mapped_column(String(6), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model_requested: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(80), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasoning_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Micro-currency (1e-6 USD) as integer to avoid float drift in SUMs.
    cost_micros: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # provider_reported | estimated | None (unknown)
    cost_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="ok")  # ok|failed|retried
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AnalyticsEvent(Base):
    """WS21 — content-free product analytics event (append-only).

    Lifecycle: user-attributed rows are removed with the account (ON DELETE
    CASCADE, same governance as primary data). Raw retention is bounded —
    repositories.purge_old_analytics_events() is the cron hook (180d default).
    See docs/production-readiness/DATA_OWNERSHIP_INVENTORY.md.
    """
    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_name_time", "name", "occurred_at"),
        Index("ix_analytics_cohort", "cohort_id"),
    )
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)  # idempotent client retries
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE"),
        index=True,
        nullable=True,  # anonymous/pre-auth beacons (documented lifecycle)
    )
    name: Mapped[str] = mapped_column(String(60))
    event_version: Mapped[int] = mapped_column(Integer, default=1)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    cohort_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    acquisition_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    anonymous_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)


class SystemFlag(Base):
    """Deployment-controlled runtime flags (e.g. the AI budget kill-switch)."""
    __tablename__ = "system_flags"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


# ═══ WS28 — Auto-RAG knowledge layer ════════════════════════════════════════
# Allowlist-first source registry → staged versioned ingestion → ACTIVE
# index. Vectors are stored as JSON float lists: the retrieval adapter is the
# seam for PostgreSQL+pgvector later (28 §3); exact cosine scoring over a
# small corpus is the documented correctness baseline.


class RagSource(Base):
    __tablename__ = "rag_source"
    id: Mapped[int] = mapped_column(primary_key=True)
    namespace: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(160))
    source_type: Mapped[str] = mapped_column(String(20), default="manual_text")  # repo_file|uploaded_file|url|manual_text
    locator: Mapped[str] = mapped_column(String(500), default="")
    owner: Mapped[str] = mapped_column(String(120), default="")
    trust_tier: Mapped[str] = mapped_column(String(2), default="T1")  # T0..T4
    allowed_use: Mapped[list] = mapped_column(JSON, default=list)
    license_type: Mapped[str] = mapped_column(String(40), default="proprietary")
    license_reference: Mapped[str] = mapped_column(String(300), default="")
    contains_personal_data: Mapped[bool] = mapped_column(Boolean, default=False)
    access_scope: Mapped[str] = mapped_column(String(12), default="internal")  # public|internal
    update_policy: Mapped[str] = mapped_column(String(12), default="manual")  # manual|scheduled
    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft|active|paused|rejected|retired
    last_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class RagDocument(Base):
    """A versioned fetched/parsed source document. Exactly ONE version per
    source is ACTIVE at a time; new versions stage, canary, then swap (28 §7
    step 9) so a failed version can never replace the last known-good one."""
    __tablename__ = "rag_document"
    __table_args__ = (Index("ix_rag_doc_source_ver", "source_id", "source_version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("rag_source.id", ondelete="CASCADE")
    )
    source_version: Mapped[int] = mapped_column(Integer, default=1)
    content_hash: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(300), default="")
    language: Mapped[str] = mapped_column(String(8), default="en")
    status: Mapped[str] = mapped_column(String(14), default="staged")  # staged|active|quarantined|retired
    supersedes_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parser_version: Mapped[str] = mapped_column(String(20), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RagChunk(Base):
    __tablename__ = "rag_chunk"
    __table_args__ = (
        Index("ix_rag_chunk_doc", "document_id", "chunk_index"),
        Index("ix_rag_chunk_status", "status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("rag_document.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    heading_path: Mapped[str] = mapped_column(String(500), default="")
    chunk_text: Mapped[str] = mapped_column(String)
    chunk_hash: Mapped[str] = mapped_column(String(64))
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    # JSON float list of the versioned embedding (pgvector swap = migration +
    # adapter change only; see retrieval adapter seam note on RagDocument).
    embedding: Mapped[list] = mapped_column(JSON, default=list)
    embedding_model: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(14), default="staged")  # staged|active|quarantined|retired
    quarantine_reasons: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RagIngestionRun(Base):
    __tablename__ = "rag_ingestion_run"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("rag_source.id", ondelete="CASCADE")
    )
    trigger: Mapped[str] = mapped_column(String(20), default="manual")  # scheduled|manual|change_detected|reindex
    status: Mapped[str] = mapped_column(String(12), default="ok")  # ok|failed|skipped
    content_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    chunks_created: Mapped[int] = mapped_column(Integer, default=0)
    chunks_reused: Mapped[int] = mapped_column(Integer, default=0)
    chunks_quarantined: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RagRetrievalEvent(Base):
    """Privacy-safe retrieval telemetry: query HASH only, never raw learner
    text. user_id nullable = anonymous/feature calls; CASCADE with account
    (same governance as analytics, WS21)."""
    __tablename__ = "rag_retrieval_event"
    __table_args__ = (Index("ix_rag_retr_use_time", "use_case", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=True
    )
    use_case: Mapped[str] = mapped_column(String(40))
    namespace_set: Mapped[list] = mapped_column(JSON, default=list)
    query_hash: Mapped[str] = mapped_column(String(64))
    retrieval_version: Mapped[str] = mapped_column(String(20), default="")
    embedding_model: Mapped[str] = mapped_column(String(60), default="")
    keyword_candidates: Mapped[int] = mapped_column(Integer, default=0)
    vector_candidates: Mapped[int] = mapped_column(Integer, default=0)
    chunk_ids: Mapped[list] = mapped_column(JSON, default=list)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

# v1.2 owner-scoped practice receipts; registered once with the shared Base.
from .practice_session import register_practice_model
PracticeSession = register_practice_model(Base)

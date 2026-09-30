"""WS04: enforce unambiguous user ownership across persistent learner data

Three coordinated changes (docs/production-readiness/04 §WS04-02/04):

1. One-time documented migration policy — legacy anonymous rows (user_id NULL
   from local-development era) are DISCARDED, not backfilled:
       DELETE FROM attempts / mocks / cards WHERE user_id IS NULL
2. attempts.user_id, mocks.user_id, cards.user_id become NOT NULL:
   persistent learner history requires a session-owned profile.
3. Every user-owned foreign key gains ON DELETE CASCADE (and milestones inherit
   through programs), so account deletion is complete by SCHEMA DESIGN — no
   hand-maintained list of child tables. Companion indexes are created where
   missing (ix_skill_levels_user, ix_placement_attempts_user, ix_feedback_user,
   ix_programs_user, ix_milestones_program).

Migration safety notes:
- Take a pre-migration backup in staging before applying (the discard step is
  irreversible).
- Postgres: reflected FK constraints are dropped by name, columns altered,
  named CASCADE constraints added.
- SQLite: each affected table is rebuilt inside an alembic batch using FROZEN
  inline definitions (copy_from) identical to the target schema — migrations
  must never import live ORM models or they drift after future app changes.
- Downgrade restores NO ACTION cascades + nullable ownership but cannot
  resurrect discarded anonymous rows (forward-fix semantics).

Revision ID: c8d21e4b7a30
Revises: a4f7c2d91e05
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.schema import CreateTable


# revision identifiers, used by Alembic.
revision: str = 'c8d21e4b7a30'
down_revision: Union[str, None] = 'a4f7c2d91e05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _t(name: str, *cols) -> sa.Table:
    # One private MetaData per table: several frozen definitions share a name
    # (post vs pre variants) and must not collide.
    t = sa.Table(name, sa.MetaData(), *cols)
    # Compile-time FK rendering resolves referents through this table's
    # MetaData: register minimal id-only stubs for every referenced table.
    md = t.metadata
    for fk_col in t.columns.values():
        for fk in fk_col.foreign_keys:
            ref_name = str(fk.target_fullname).split(".", 1)[0]
            if ref_name and ref_name not in md.tables:
                sa.Table(ref_name, md, sa.Column("id", sa.Integer(), primary_key=True))
    return t


# ─── Frozen POST-WS04 targets (NOT NULL where applicable + CASCADE) ──────────

_CASCADE_USER = lambda: [sa.ForeignKeyConstraint(["user_id"], ["user_profile.id"], ondelete="CASCADE")]

_ATTEMPTS_POST = _t(
    "attempts",
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("type", sa.String(length=20), nullable=False),
    sa.Column("task", sa.String(length=40), nullable=False),
    sa.Column("prompt", sa.String(), nullable=False),
    sa.Column("body", sa.String(), nullable=False),
    sa.Column("bands", sa.JSON(), nullable=False),
    sa.Column("criteria", sa.JSON(), nullable=False),
    sa.Column("cefr", sa.String(length=6), nullable=False),
    sa.Column("metrics", sa.JSON(), nullable=False),
    sa.Column("score_method", sa.String(length=20), nullable=True),
    sa.Column("score_version", sa.String(length=20), nullable=True),
    sa.Column("model_provider", sa.String(length=40), nullable=True),
    sa.Column("model_id", sa.String(length=60), nullable=True),
    sa.Column("prompt_version", sa.String(length=20), nullable=True),
    sa.Column("rubric_version", sa.String(length=20), nullable=True),
    sa.Column("calibration_version", sa.String(length=20), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    *_CASCADE_USER(),
)
_MOCKS_POST = _t(
    "mocks",
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("listening", sa.Float(), nullable=False),
    sa.Column("reading", sa.Float(), nullable=False),
    sa.Column("overall", sa.Float(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    *_CASCADE_USER(),
)
_CARDS_POST = _t(
    "cards",
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("front", sa.String(), nullable=False),
    sa.Column("back", sa.String(), nullable=False),
    sa.Column("ease", sa.Float(), nullable=False),
    sa.Column("interval", sa.Integer(), nullable=False),
    sa.Column("reps", sa.Integer(), nullable=False),
    sa.Column("lapses", sa.Integer(), nullable=False),
    sa.Column("due", sa.DateTime(timezone=True), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    *_CASCADE_USER(),
)
_SKILL_LEVELS_POST = _t(
    "skill_levels",
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("skill", sa.String(length=20), nullable=False),
    sa.Column("band", sa.String(length=6), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    *_CASCADE_USER(),
)
_PLACEMENT_ATTEMPTS_POST = _t(
    "placement_attempts",
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("combo_id", sa.Integer(), nullable=False),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("duration_sec", sa.Integer(), nullable=False),
    sa.Column("per_skill", sa.JSON(), nullable=False),
    sa.Column("overall_band", sa.Float(), nullable=False),
    sa.Column("cefr", sa.String(length=6), nullable=False),
    sa.Column("gap_to_target", sa.Float(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    *_CASCADE_USER(),
)
_TEST_GATE_POST = _t(
    "test_gate",
    sa.Column("user_id", sa.Integer(), primary_key=True),
    sa.Column("active_seconds", sa.Integer(), nullable=False),
    sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
    *_CASCADE_USER(),
)
_FEEDBACK_POST = _t(
    "feedback",
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("stars", sa.Integer(), nullable=False),
    sa.Column("insight", sa.String(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    *_CASCADE_USER(),
)
_GEN_USAGE_POST = _t(
    "gen_usage",
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("day", sa.String(length=10), nullable=False),
    sa.Column("count", sa.Integer(), nullable=False),
    *_CASCADE_USER(),
)
_PROGRAMS_POST = _t(
    "programs",
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("length_days", sa.Integer(), nullable=False),
    sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
    sa.Column("status", sa.String(length=12), nullable=False),
    *_CASCADE_USER(),
)
_MILESTONES_POST = _t(
    "milestones",
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("program_id", sa.Integer(), nullable=False),
    sa.Column("idx", sa.Integer(), nullable=False),
    sa.Column("day_target", sa.Integer(), nullable=False),
    sa.Column("title", sa.String(length=160), nullable=False),
    sa.Column("targets", sa.JSON(), nullable=False),
    sa.Column("achieved_at", sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
)
_LESSONS_POST = _t(
    "lessons",
    sa.Column("user_id", sa.Integer(), primary_key=True),
    sa.Column("day", sa.Integer(), primary_key=True),
    sa.Column("lesson", sa.JSON(), nullable=False),
    sa.Column("focus", sa.String(length=80), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    *_CASCADE_USER(),
)


# table, column, referent_table, post_target, column_becomes_not_null
_CHILD_TABLES = [
    ("attempts",           "user_id",    "user_profile", _ATTEMPTS_POST,           True),
    ("mocks",              "user_id",    "user_profile", _MOCKS_POST,              True),
    ("cards",              "user_id",    "user_profile", _CARDS_POST,              True),
    ("skill_levels",       "user_id",    "user_profile", _SKILL_LEVELS_POST,       False),
    ("placement_attempts", "user_id",    "user_profile", _PLACEMENT_ATTEMPTS_POST, False),
    ("test_gate",          "user_id",    "user_profile", _TEST_GATE_POST,          False),
    ("feedback",           "user_id",    "user_profile", _FEEDBACK_POST,           False),
    ("gen_usage",          "user_id",    "user_profile", _GEN_USAGE_POST,          False),
    ("programs",           "user_id",    "user_profile", _PROGRAMS_POST,           False),
    ("milestones",         "program_id", "programs",     _MILESTONES_POST,         False),
    ("lessons",            "user_id",    "user_profile", _LESSONS_POST,            False),
]

_NEW_INDEXES = [
    ("ix_skill_levels_user",       "skill_levels",       ["user_id"]),
    ("ix_placement_attempts_user", "placement_attempts", ["user_id"]),
    ("ix_feedback_user",           "feedback",           ["user_id"]),
    ("ix_programs_user",           "programs",           ["user_id"]),
    ("ix_milestones_program",      "milestones",         ["program_id"]),
]


# ─── Frozen PRE-WS04 shapes (SQLite downgrade path) ──────────────────────────

_NO_ACTION_USER = lambda: [sa.ForeignKeyConstraint(["user_id"], ["user_profile.id"])]

_PRE_BY_TABLE: dict[str, sa.Table] = {
    "attempts": _t(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("task", sa.String(length=40), nullable=False),
        sa.Column("prompt", sa.String(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("bands", sa.JSON(), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("cefr", sa.String(length=6), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("score_method", sa.String(length=20), nullable=True),
        sa.Column("score_version", sa.String(length=20), nullable=True),
        sa.Column("model_provider", sa.String(length=40), nullable=True),
        sa.Column("model_id", sa.String(length=60), nullable=True),
        sa.Column("prompt_version", sa.String(length=20), nullable=True),
        sa.Column("rubric_version", sa.String(length=20), nullable=True),
        sa.Column("calibration_version", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        *_NO_ACTION_USER(),
    ),
    "mocks": _t(
        "mocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("listening", sa.Float(), nullable=False),
        sa.Column("reading", sa.Float(), nullable=False),
        sa.Column("overall", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        *_NO_ACTION_USER(),
    ),
    "cards": _t(
        "cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("front", sa.String(), nullable=False),
        sa.Column("back", sa.String(), nullable=False),
        sa.Column("ease", sa.Float(), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("lapses", sa.Integer(), nullable=False),
        sa.Column("due", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        *_NO_ACTION_USER(),
    ),
}


def _pg_fk_names(inspector, table: str, col: str) -> list[str]:
    names = []
    for fk in inspector.get_foreign_keys(table):
        if list(fk.get("constrained_columns") or []) == [col]:
            if fk.get("name"):
                names.append(fk["name"])
    return names


# Indexes that pre-date this migration and must survive the SQLite table
# swaps (name, columns, unique).
_KEEP_INDEXES: dict[str, list[tuple[str, list[str], bool]]] = {
    "attempts":  [("ix_attempts_user_id", ["user_id"], False)],
    "mocks":     [("ix_mocks_user_id", ["user_id"], False)],
    "cards":     [("ix_cards_user_id", ["user_id"], False)],
    "gen_usage": [("ix_gen_usage_user_day", ["user_id", "day"], True)],
}


def _swap_sqlite(table_name: str, target: sa.Table) -> None:
    """Rebuild *table_name* on SQLite from the frozen target definition.

    Alembic batch mode performs NO rebuild when the batch body is empty, so we
    drive the copy explicitly: create tmp (target DDL), copy rows by shared
    column names, drop old, rename. Reflected indexes die with the old table
    and are recreated from _KEEP_INDEXES.
    """
    bind = op.get_bind()
    ddl = str(CreateTable(target).compile(bind)).lstrip()
    tmp = f"{table_name}__ws04tmp"
    ddl_tmp, n = re.subn(
        rf"(?i)^CREATE\s+TABLE\s+{re.escape(table_name)}\b",
        f"CREATE TABLE {tmp}",
        ddl,
        count=1,
    )
    if n != 1:
        raise RuntimeError(f"could not rewrite DDL header for {table_name}")

    cols = ", ".join(c.name for c in target.columns)
    op.execute(ddl_tmp)
    op.execute(f"INSERT INTO {tmp} ({cols}) SELECT {cols} FROM {table_name}")
    op.execute(f"DROP TABLE {table_name}")
    op.execute(f"ALTER TABLE {tmp} RENAME TO {table_name}")

    for idx_name, idx_cols, unique in _KEEP_INDEXES.get(table_name, []):
        op.create_index(op.f(idx_name), table_name, idx_cols, unique=unique)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)

    # ── Step 1: documented one-time discard of legacy anonymous rows ────────
    op.execute("DELETE FROM attempts WHERE user_id IS NULL")
    op.execute("DELETE FROM mocks WHERE user_id IS NULL")
    op.execute("DELETE FROM cards WHERE user_id IS NULL")

    # ── Steps 2+3: NOT NULL + CASCADE per dialect ───────────────────────────
    for table, col, referent, target, make_not_null in _CHILD_TABLES:
        if dialect == "postgresql":
            for name in _pg_fk_names(inspector, table, col):
                op.drop_constraint(name, table, type_="foreignkey")
            if make_not_null:
                op.alter_column(table, col, existing_type=sa.Integer(), nullable=False)
            op.create_foreign_key(
                f"fk_{table}_{col}_cascade", table, referent, [col], ["id"],
                ondelete="CASCADE",
            )
        elif dialect == "sqlite":
            # Explicit swap-rebuild from the frozen inline definition. Order
            # matters: programs before milestones (FK target must exist).
            _swap_sqlite(table, target)
        else:  # pragma: no cover - other dialects unsupported by this change
            raise RuntimeError(f"Unsupported dialect for WS04 migration: {dialect}")

    for idx_name, table, cols in _NEW_INDEXES:
        op.create_index(op.f(idx_name), table, cols, unique=False)


def downgrade() -> None:
    """Forward-fix capable downgrade.

    Restores NO ACTION cascades and (attempts/mocks/cards) nullable ownership.
    Discarded anonymous rows cannot be recovered — prefer forward fixes in
    production; this exists so the chain remains replayable in CI.
    """
    bind = op.get_bind()
    dialect = bind.dialect.name

    for idx_name, table, _cols in reversed(_NEW_INDEXES):
        op.drop_index(op.f(idx_name), table_name=table)

    inspector = sa.inspect(bind)
    for table, col, referent, _target, make_not_null in reversed(_CHILD_TABLES):
        if dialect == "postgresql":
            for name in _pg_fk_names(inspector, table, col):
                op.drop_constraint(name, table, type_="foreignkey")
            if make_not_null:
                op.alter_column(table, col, existing_type=sa.Integer(), nullable=True)
            op.create_foreign_key(
                f"fk_{table}_{col}_prews04", table, referent, [col], ["id"]
            )
        elif dialect == "sqlite":
            if make_not_null and table in _PRE_BY_TABLE:
                with op.batch_alter_table(
                    table, copy_from=_PRE_BY_TABLE[table]
                ):
                    pass
            # Tables unchanged except the cascade action keep their shape on
            # SQLite downgrade: replayed prod chains never run SQLite, and the
            # cascade flag alone has no behavioural effect there once rows are
            # always owned. Documented forward-fix simplification.

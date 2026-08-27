"""WS07: job records, append-only AI usage ledger, system flags

Additive migration (docs/production-readiness/07 §WS07-03/08):

1. ``jobs`` — persistent job records for heavy/queued work: unguessable UUID
   id, user-scoped status lookup, idempotency binding
   (user_id, idempotency_key) UNIQUE, safe error surface, provider/model
   metadata, retry counter, bounded retention via expires_at.
2. ``ai_usage_ledger`` — append-only provider usage/cost ledger (WS07-08).
   The single accounting source of truth for AI spend; WS27 evolves it through
   coordinated migrations (no second usage table). Accounting metadata only —
   never learner content. user_id is ON DELETE SET NULL so the financial
   record survives account deletion without keeping the identifier.
3. ``system_flags`` — runtime flags (the AI budget kill-switch), readable by
   every API worker and Celery worker.

Downgrade drops the three tables. The ledger is append-only by contract, so a
downgrade discards cost history — acceptable: it is a full re-derivable-from-
provider-billing operational record, not learner data.

Revision ID: b7e4d2f19c08
Revises: c8d21e4b7a30
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e4d2f19c08'
down_revision: Union[str, None] = 'c8d21e4b7a30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("queue", sa.String(length=20), nullable=False,
                  server_default="default"),
        sa.Column("status", sa.String(length=12), nullable=False,
                  server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False,
                  server_default=""),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("error_message", sa.String(length=200), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("model_requested", sa.String(length=80), nullable=True),
        sa.Column("model_used", sa.String(length=80), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_profile.id"], ondelete="CASCADE"
        ),
    )
    # The idempotency key embeds its owner ("...:u:<id|sys>:<key>") so one
    # unique index binds BOTH user jobs and system jobs (NULL user_id rows
    # are DISTINCT in SQL unique indexes — see models.Job).
    op.create_index("ix_jobs_idem", "jobs", ["idempotency_key"], unique=True)
    op.create_index("ix_jobs_user_created", "jobs", ["user_id", "created_at"])

    op.create_table(
        "ai_usage_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("cost_center", sa.String(length=40), nullable=False),
        sa.Column("op", sa.String(length=40), nullable=False),
        sa.Column("skill", sa.String(length=20), nullable=True),
        sa.Column("band", sa.String(length=6), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("model_requested", sa.String(length=80), nullable=True),
        sa.Column("model_used", sa.String(length=80), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_micros", sa.Integer(), nullable=True),
        sa.Column("cost_source", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=12), nullable=False,
                  server_default="ok"),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_profile.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_ledger_user_created", "ai_usage_ledger",
                    ["user_id", "created_at"])
    op.create_index("ix_ledger_center_created", "ai_usage_ledger",
                    ["cost_center", "created_at"])

    op.create_table(
        "system_flags",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", sa.String(length=255), nullable=False,
                  server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("system_flags")
    op.drop_index("ix_ledger_center_created", table_name="ai_usage_ledger")
    op.drop_index("ix_ledger_user_created", table_name="ai_usage_ledger")
    op.drop_table("ai_usage_ledger")
    op.drop_index("ix_jobs_user_created", table_name="jobs")
    op.drop_index("ix_jobs_idem", table_name="jobs")
    op.drop_table("jobs")

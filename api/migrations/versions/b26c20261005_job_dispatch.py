"""Durable job delivery intents; backfill queued work without replaying running jobs.

Revision ID: b26c20261005
Revises: a12c20260929
"""
from alembic import op
import sqlalchemy as sa
revision = "b26c20261005"
down_revision = "a12c20260929"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("job_dispatch",
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False))
    op.create_index("ix_job_dispatch_due", "job_dispatch", ["not_before"])
    op.execute(sa.text("INSERT INTO job_dispatch (job_id, not_before, attempts) "
                       "SELECT id, CURRENT_TIMESTAMP, 0 FROM jobs WHERE status = 'queued'"))


def downgrade():
    # Stop/drain workers first; removing intents abandons pending delivery retries.
    op.drop_index("ix_job_dispatch_due", table_name="job_dispatch")
    op.drop_table("job_dispatch")

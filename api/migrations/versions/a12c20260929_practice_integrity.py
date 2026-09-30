"""Owner-scoped practice snapshots; migrate before serving the v1.2 web client.

Revision ID: a12c20260929
Revises: f1a2b3c4d5e6
"""
from alembic import op
import sqlalchemy as sa
revision = "a12c20260929"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("practice_sessions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill", sa.String(20), nullable=False),
        sa.Column("band", sa.String(6), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("answer_hash", sa.String(64), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_practice_owner_expiry", "practice_sessions", ["user_id", "expires_at"])
    # Do not silently delete or relabel old learner records. V1.2 readers filter
    # legacy client-scored practice; historical records remain available for export.


def downgrade():
    # Submitted history remains in attempts. Only short-lived session receipts drop.
    op.drop_index("ix_practice_owner_expiry", table_name="practice_sessions")
    op.drop_table("practice_sessions")

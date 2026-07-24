"""test_gate feedback genusage

Revision ID: e631087d0920
Revises: 9413f2a93a7e
Create Date: 2026-07-25 00:27:47.238309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e631087d0920'
down_revision: Union[str, None] = '9413f2a93a7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "test_gate",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user_profile.id"), primary_key=True),
        sa.Column("active_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user_profile.id"), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("insight", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "gen_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user_profile.id"), nullable=False),
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_gen_usage_user_day", "gen_usage", ["user_id", "day"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_gen_usage_user_day", table_name="gen_usage")
    op.drop_table("gen_usage")
    op.drop_table("feedback")
    op.drop_table("test_gate")

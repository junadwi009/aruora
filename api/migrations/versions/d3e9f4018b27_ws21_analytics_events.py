"""WS21: analytics events + server-owned acquisition/cohort dimensions

- analytics_events: append-only, content-free product analytics. event_id is a
  client-retryable idempotency key (PK). user_id is NULLABLE for pre-auth
  beacons but CASCADEs on account deletion (same governance as primary data).
- user_profile.acquisition_source / cohort_id: server-validated closed-set
  dimensions (app.domain.analytics); never client free-text segmentation.

Revision ID: d3e9f4018b27
Revises: b51f7aa3c9d0
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e9f4018b27'
down_revision: Union[str, None] = 'b51f7aa3c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'analytics_events',
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('event_version', sa.Integer(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cohort_id', sa.String(length=40), nullable=True),
        sa.Column('acquisition_source', sa.String(length=40), nullable=True),
        sa.Column('anonymous_id', sa.String(length=64), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user_profile.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('event_id'),
    )
    op.create_index(op.f('ix_analytics_events_user_id'), 'analytics_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_analytics_name_time'), 'analytics_events', ['name', 'occurred_at'], unique=False)
    op.create_index(op.f('ix_analytics_cohort'), 'analytics_events', ['cohort_id'], unique=False)

    op.add_column('user_profile', sa.Column('acquisition_source', sa.String(length=40), nullable=True))
    op.add_column('user_profile', sa.Column('cohort_id', sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profile', 'cohort_id')
    op.drop_column('user_profile', 'acquisition_source')
    op.drop_index(op.f('ix_analytics_cohort'), table_name='analytics_events')
    op.drop_index(op.f('ix_analytics_name_time'), table_name='analytics_events')
    op.drop_index(op.f('ix_analytics_events_user_id'), table_name='analytics_events')
    op.drop_table('analytics_events')

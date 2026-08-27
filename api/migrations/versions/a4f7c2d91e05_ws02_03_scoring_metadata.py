"""WS02-03: add AI scoring metadata envelope to attempts

Revision ID: a4f7c2d91e05
Revises: e631087d0920
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4f7c2d91e05'
down_revision: Union[str, None] = 'e631087d0920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('attempts', sa.Column('score_method', sa.String(length=20), nullable=True))
    op.add_column('attempts', sa.Column('score_version', sa.String(length=20), nullable=True))
    op.add_column('attempts', sa.Column('model_provider', sa.String(length=40), nullable=True))
    op.add_column('attempts', sa.Column('model_id', sa.String(length=60), nullable=True))
    op.add_column('attempts', sa.Column('prompt_version', sa.String(length=20), nullable=True))
    op.add_column('attempts', sa.Column('rubric_version', sa.String(length=20), nullable=True))
    op.add_column('attempts', sa.Column('calibration_version', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('attempts', 'calibration_version')
    op.drop_column('attempts', 'rubric_version')
    op.drop_column('attempts', 'prompt_version')
    op.drop_column('attempts', 'model_id')
    op.drop_column('attempts', 'model_provider')
    op.drop_column('attempts', 'score_version')
    op.drop_column('attempts', 'score_method')

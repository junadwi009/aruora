"""WS27: evolve generated_sets into Task Bank semantics + task_exposure

Stage B of the WS27 migration plan (docs/production-readiness/27 §26):

1. ``generated_sets`` gains lifecycle/provenance/economics columns:
   - status (active | quarantined | retired) — serving filters on it;
   - pool_kind, content_hash (exact-duplicate rejection), quality_flags,
     generation_meta (model/provider/prompt provenance), gen_cost_micros,
     serve_count, activated_at, retired_at.
   Existing rows (seed + legacy generated inventory) default to ``active``
   and get a canonical content hash backfilled in Python — migrations must
   not import live ORM models, so the hash is computed inline.
2. New ``task_exposure`` table: per-user served-task history for anti-repeat
   selection and repeat-rate metrics. No learner content is stored. Both FKs
   CASCADE (account deletion removes history; set removal removes exposure).

Downgrade drops task_exposure and the added columns. serve_count/exposure
history is re-derivable operational data, not learner content.

Revision ID: e8c4a6f20d51
Revises: d3e9f4018b27
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

import hashlib
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8c4a6f20d51'
down_revision: Union[str, None] = 'd3e9f4018b27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _canonical_hash(payload) -> str:
    """Same canonicalisation as app.services.task_pool.content_hash —
    duplicated inline because migrations never import live app modules."""
    try:
        canon = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"))
    except (TypeError, ValueError):
        return ""
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def upgrade() -> None:
    with op.batch_alter_table("generated_sets") as batch:
        batch.add_column(sa.Column("status", sa.String(length=12),
                                   nullable=False, server_default="active"))
        batch.add_column(sa.Column("pool_kind", sa.String(length=20),
                                   nullable=False, server_default="practice_adaptive"))
        batch.add_column(sa.Column("content_hash", sa.String(length=64),
                                   nullable=True))
        batch.add_column(sa.Column("quality_flags", sa.JSON(), nullable=False,
                                   server_default="{}"))
        batch.add_column(sa.Column("generation_meta", sa.JSON(), nullable=False,
                                   server_default="{}"))
        batch.add_column(sa.Column("gen_cost_micros", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("serve_count", sa.Integer(), nullable=False,
                                   server_default="0"))
        batch.add_column(sa.Column("activated_at", sa.DateTime(timezone=True),
                                   nullable=True))
        batch.add_column(sa.Column("retired_at", sa.DateTime(timezone=True),
                                   nullable=True))

    # Backfill canonical hashes for existing inventory (seeds + legacy rows).
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, payload FROM generated_sets WHERE content_hash IS NULL"
    )).fetchall()
    for row_id, payload in rows:
        conn.execute(sa.text(
            "UPDATE generated_sets SET content_hash = :h WHERE id = :i"
        ), {"h": _canonical_hash(payload), "i": row_id})

    op.create_index("ix_sets_bucket_status", "generated_sets",
                    ["skill", "band", "status"])
    # Unique per bucket: NULL hashes (unhashable legacy payloads) are distinct
    # in SQL unique indexes, so only hashable rows participate in dedup.
    op.create_index("ix_sets_bucket_hash", "generated_sets",
                    ["skill", "band", "content_hash"], unique=True)

    op.create_table(
        "task_exposure",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("set_id", sa.Integer(), nullable=False),
        sa.Column("served_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("selection_context", sa.String(length=20), nullable=False,
                  server_default="practice"),
        sa.Column("repeat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["user_id"], ["user_profile.id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["set_id"], ["generated_sets.id"],
                                ondelete="CASCADE"),
    )
    op.create_index("ix_exposure_user_set_time", "task_exposure",
                    ["user_id", "set_id", "served_at"])
    op.create_index("ix_exposure_set_time", "task_exposure",
                    ["set_id", "served_at"])
    op.create_index("ix_exposure_user_time", "task_exposure",
                    ["user_id", "served_at"])


def downgrade() -> None:
    op.drop_table("task_exposure")
    op.drop_index("ix_sets_bucket_hash", table_name="generated_sets")
    op.drop_index("ix_sets_bucket_status", table_name="generated_sets")
    with op.batch_alter_table("generated_sets") as batch:
        batch.drop_column("retired_at")
        batch.drop_column("activated_at")
        batch.drop_column("serve_count")
        batch.drop_column("gen_cost_micros")
        batch.drop_column("generation_meta")
        batch.drop_column("quality_flags")
        batch.drop_column("content_hash")
        batch.drop_column("pool_kind")
        batch.drop_column("status")

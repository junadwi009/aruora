"""WS28: RAG knowledge layer (allowlist-first sources, staged documents,
chunk index, ingestion runs, retrieval telemetry)

Vectors are stored as JSON float lists — the retrieval adapter is the seam
for a PostgreSQL+pgvector swap (exact cosine over the small Phase-A corpus is
the documented correctness baseline). embedding_model/version is persisted on
every chunk so model migration (28 §12) is a versioned backfill, never an
in-place overwrite.

Revision ID: f1a2b3c4d5e6
Revises: e8c4a6f20d51
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e8c4a6f20d51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rag_source',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('namespace', sa.String(length=40), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('locator', sa.String(length=500), nullable=False),
        sa.Column('owner', sa.String(length=120), nullable=False),
        sa.Column('trust_tier', sa.String(length=2), nullable=False),
        sa.Column('allowed_use', sa.JSON(), nullable=False),
        sa.Column('license_type', sa.String(length=40), nullable=False),
        sa.Column('license_reference', sa.String(length=300), nullable=False),
        sa.Column('contains_personal_data', sa.Boolean(), nullable=False),
        sa.Column('access_scope', sa.String(length=12), nullable=False),
        sa.Column('update_policy', sa.String(length=12), nullable=False),
        sa.Column('status', sa.String(length=12), nullable=False),
        sa.Column('last_content_hash', sa.String(length=64), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'rag_document',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('source_version', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('language', sa.String(length=8), nullable=False),
        sa.Column('status', sa.String(length=14), nullable=False),
        sa.Column('supersedes_document_id', sa.Integer(), nullable=True),
        sa.Column('parser_version', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['rag_source.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rag_doc_source_ver'), 'rag_document',
                    ['source_id', 'source_version'], unique=False)
    op.create_table(
        'rag_chunk',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('heading_path', sa.String(length=500), nullable=False),
        sa.Column('chunk_text', sa.String(), nullable=False),
        sa.Column('chunk_hash', sa.String(length=64), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('embedding', sa.JSON(), nullable=False),
        sa.Column('embedding_model', sa.String(length=60), nullable=False),
        sa.Column('status', sa.String(length=14), nullable=False),
        sa.Column('quarantine_reasons', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['rag_document.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rag_chunk_doc'), 'rag_chunk', ['document_id', 'chunk_index'], unique=False)
    op.create_index(op.f('ix_rag_chunk_status'), 'rag_chunk', ['status'], unique=False)
    op.create_table(
        'rag_ingestion_run',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('trigger', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=12), nullable=False),
        sa.Column('content_changed', sa.Boolean(), nullable=False),
        sa.Column('chunks_created', sa.Integer(), nullable=False),
        sa.Column('chunks_reused', sa.Integer(), nullable=False),
        sa.Column('chunks_quarantined', sa.Integer(), nullable=False),
        sa.Column('error_code', sa.String(length=40), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['rag_source.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'rag_retrieval_event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('use_case', sa.String(length=40), nullable=False),
        sa.Column('namespace_set', sa.JSON(), nullable=False),
        sa.Column('query_hash', sa.String(length=64), nullable=False),
        sa.Column('retrieval_version', sa.String(length=20), nullable=False),
        sa.Column('embedding_model', sa.String(length=60), nullable=False),
        sa.Column('keyword_candidates', sa.Integer(), nullable=False),
        sa.Column('vector_candidates', sa.Integer(), nullable=False),
        sa.Column('chunk_ids', sa.JSON(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user_profile.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rag_retr_use_time'), 'rag_retrieval_event',
                    ['use_case', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_rag_retr_use_time'), table_name='rag_retrieval_event')
    op.drop_table('rag_retrieval_event')
    op.drop_table('rag_ingestion_run')
    op.drop_index(op.f('ix_rag_chunk_status'), table_name='rag_chunk')
    op.drop_index(op.f('ix_rag_chunk_doc'), table_name='rag_chunk')
    op.drop_table('rag_chunk')
    op.drop_index(op.f('ix_rag_doc_source_ver'), table_name='rag_document')
    op.drop_table('rag_document')
    op.drop_table('rag_source')

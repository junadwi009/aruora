"""WS03: identity/session security — server-side sessions, one-time tokens,
admin audit trail, and the email-verification flag.

Adds (docs/production-readiness/03 §WS03-01/05/06/07):

1. ``auth_session`` — authoritative server-side session state. The browser
   keeps only an opaque token; this row is what gets revoked. ``id`` stores
   sha256(token) so a database leak cannot mint cookies. Rows carry no
   learner content (user id, csrf token, tiny flags, device metadata only).
   ON DELETE CASCADE ties every row to its account.
2. ``auth_one_time_token`` — single-use expiring tokens for password reset
   and email verification. Only sha256(token) is persisted; used_at makes
   consumption strictly one-time. Cascades with the account.
3. ``admin_audit`` — append-only privileged-action trail. Deliberately NOT
   user-owned: rows must survive actor deletion (actor_user_id ON DELETE
   SET NULL; target ids are denormalised plain integers). Retention policy
   is reviewed per release; rows never contain learner content.
4. ``user_profile.email_verified`` — WS03-05 email-ownership state. Backfill
   policy: every account that existed BEFORE this migration is marked
   verified (true). They registered under the previous self-hosted trust
   model; forcing re-verification of existing learners would be a silent
   lockout. New registrations start unverified.

Downgrade drops the new tables/column; audit history is intentionally lost on
downgrade (forward-fix semantics, documented).

Revision ID: b51f7aa3c9d0
Revises: b7e4d2f19c08 (chained after the WS07 jobs/usage-ledger migration to
keep a single head; both branches were additive from c8d21e4b7a30)
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b51f7aa3c9d0'
down_revision: Union[str, None] = 'b7e4d2f19c08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_session",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("user_profile.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("csrf_token", sa.String(length=64), nullable=False),
        sa.Column("flags", sa.JSON(), nullable=False),
        sa.Column("remember", sa.Boolean(), nullable=False),
        sa.Column("device", sa.String(length=200), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_auth_session_user", "auth_session", ["user_id"])
    op.create_index("ix_auth_session_revoked", "auth_session", ["revoked_at"])

    op.create_table(
        "auth_one_time_token",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("user_profile.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_ip_hash", sa.String(length=64), nullable=False),
        sa.Column("request_ua", sa.String(length=200), nullable=False),
    )
    op.create_index("ix_ott_user", "auth_one_time_token", ["user_id"])
    op.create_index("ix_ott_token_hash", "auth_one_time_token", ["token_hash"], unique=True)

    op.create_table(
        "admin_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(),
                  sa.ForeignKey("user_profile.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.add_column(
        "user_profile",
        sa.Column("email_verified", sa.Boolean(),
                  server_default=sa.false(), nullable=False),
    )
    # Backfill: pre-existing accounts are trusted as verified (see docstring).
    op.execute("UPDATE user_profile SET email_verified = true WHERE email IS NOT NULL")


def downgrade() -> None:
    op.drop_column("user_profile", "email_verified")
    op.drop_table("admin_audit")
    op.drop_table("auth_one_time_token")
    op.drop_index("ix_auth_session_user", table_name="auth_session")
    op.drop_index("ix_auth_session_revoked", table_name="auth_session")
    op.drop_table("auth_session")

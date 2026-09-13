"""add revoked_tokens table

Revision ID: 0003_revoked_tokens
Revises: 0002_assistant_messages
Create Date: 2026-09-13

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_revoked_tokens"
down_revision = "0002_assistant_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(32), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_table("revoked_tokens")

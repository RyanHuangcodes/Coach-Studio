"""create drafts table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drafts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sport", sa.String(60), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("duration_minutes >= 5 AND duration_minutes <= 240", name="draft_duration_range"),
    )
    op.create_index("ix_drafts_user_id", "drafts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_drafts_user_id", table_name="drafts")
    op.drop_table("drafts")

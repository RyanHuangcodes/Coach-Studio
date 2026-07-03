"""create plans table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plans",
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
        sa.Column(
            "source_draft_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("drafts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint("duration_minutes >= 5 AND duration_minutes <= 240", name="plan_duration_range"),
    )
    op.create_index("ix_plans_user_id", "plans", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_plans_user_id", table_name="plans")
    op.drop_table("plans")

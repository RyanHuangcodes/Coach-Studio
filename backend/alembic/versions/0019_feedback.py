"""coach session feedback for players

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("coach_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", UUID(as_uuid=False), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_label", sa.String(length=120), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_feedback_coach_id", "feedback", ["coach_id"])
    op.create_index("ix_feedback_player_id", "feedback", ["player_id"])
    op.create_index("ix_feedback_created_at", "feedback", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_created_at", table_name="feedback")
    op.drop_index("ix_feedback_player_id", table_name="feedback")
    op.drop_index("ix_feedback_coach_id", table_name="feedback")
    op.drop_table("feedback")

"""create completed_sessions history tables (session + snapshotted players/drills)

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "completed_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("sport", sa.String(60), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_completed_sessions_user_id", "completed_sessions", ["user_id"])

    op.create_table(
        "completed_session_players",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("completed_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("player_name", sa.String(80), nullable=False),
        sa.Column("tier_name", sa.String(40), nullable=True),
    )
    op.create_index(
        "ix_completed_session_players_session_id", "completed_session_players", ["session_id"]
    )

    op.create_table(
        "completed_session_drills",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("completed_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("repeats", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_completed_session_drills_session_id", "completed_session_drills", ["session_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_completed_session_drills_session_id", table_name="completed_session_drills")
    op.drop_table("completed_session_drills")
    op.drop_index("ix_completed_session_players_session_id", table_name="completed_session_players")
    op.drop_table("completed_session_players")
    op.drop_index("ix_completed_sessions_user_id", table_name="completed_sessions")
    op.drop_table("completed_sessions")

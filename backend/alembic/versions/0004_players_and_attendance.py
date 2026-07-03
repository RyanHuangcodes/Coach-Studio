"""create tiers, players, practices, attendance_records tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tiers",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tiers_user_id", "tiers", ["user_id"])

    op.create_table(
        "players",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column(
            "tier_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("tiers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_players_user_id", "players", ["user_id"])

    op.create_table(
        "practices",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "plan_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("plans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "date", name="practice_user_date_unique"),
    )
    op.create_index("ix_practices_user_id", "practices", ["user_id"])

    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "practice_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("practices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "player_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("practice_id", "player_id", name="attendance_practice_player_unique"),
    )
    op.create_index("ix_attendance_records_practice_id", "attendance_records", ["practice_id"])
    op.create_index("ix_attendance_records_player_id", "attendance_records", ["player_id"])


def downgrade() -> None:
    op.drop_index("ix_attendance_records_player_id", table_name="attendance_records")
    op.drop_index("ix_attendance_records_practice_id", table_name="attendance_records")
    op.drop_table("attendance_records")

    op.drop_index("ix_practices_user_id", table_name="practices")
    op.drop_table("practices")

    op.drop_index("ix_players_user_id", table_name="players")
    op.drop_table("players")

    op.drop_index("ix_tiers_user_id", table_name="tiers")
    op.drop_table("tiers")

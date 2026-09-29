"""player logins + training access + assignments + messages

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-27

Adds the second user type (players log in) and the communication features:
a role on users, a login link + training-access flag on players, plus
`assignments` (coach -> player to-dos) and `messages` (1:1 coach/player chat).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("role", sa.String(length=12), nullable=False, server_default="coach")
    )
    op.create_check_constraint("user_role_valid", "users", "role IN ('coach', 'player')")

    op.add_column("players", sa.Column("login_user_id", UUID(as_uuid=False), nullable=True))
    op.add_column(
        "players",
        sa.Column("can_view_trainings", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_unique_constraint("players_login_user_id_unique", "players", ["login_user_id"])
    op.create_foreign_key(
        "players_login_user_id_fkey", "players", "users", ["login_user_id"], ["id"], ondelete="SET NULL"
    )

    op.create_table(
        "assignments",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("coach_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", UUID(as_uuid=False), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("done", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("category IN ('skills', 'strength', 'recovery')", name="assignment_category_valid"),
    )
    op.create_index("ix_assignments_coach_id", "assignments", ["coach_id"])
    op.create_index("ix_assignments_player_id", "assignments", ["player_id"])

    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("player_id", UUID(as_uuid=False), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_role", sa.String(length=12), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("sender_role IN ('coach', 'player')", name="message_sender_role_valid"),
    )
    op.create_index("ix_messages_player_id", "messages", ["player_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_player_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_assignments_player_id", table_name="assignments")
    op.drop_index("ix_assignments_coach_id", table_name="assignments")
    op.drop_table("assignments")
    op.drop_constraint("players_login_user_id_fkey", "players", type_="foreignkey")
    op.drop_constraint("players_login_user_id_unique", "players", type_="unique")
    op.drop_column("players", "can_view_trainings")
    op.drop_column("players", "login_user_id")
    op.drop_constraint("user_role_valid", "users", type_="check")
    op.drop_column("users", "role")

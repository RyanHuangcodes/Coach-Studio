"""create practice_groups and practice_group_players tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "practice_groups",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "practice_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("practices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("group_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("practice_id", "group_number", name="practice_group_number_unique"),
    )
    op.create_index("ix_practice_groups_practice_id", "practice_groups", ["practice_id"])

    op.create_table(
        "practice_group_players",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("practice_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "player_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("group_id", "player_id", name="group_player_unique"),
    )
    op.create_index("ix_practice_group_players_group_id", "practice_group_players", ["group_id"])
    op.create_index("ix_practice_group_players_player_id", "practice_group_players", ["player_id"])


def downgrade() -> None:
    op.drop_index("ix_practice_group_players_player_id", table_name="practice_group_players")
    op.drop_index("ix_practice_group_players_group_id", table_name="practice_group_players")
    op.drop_table("practice_group_players")

    op.drop_index("ix_practice_groups_practice_id", table_name="practice_groups")
    op.drop_table("practice_groups")

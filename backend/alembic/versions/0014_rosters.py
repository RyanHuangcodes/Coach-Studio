"""rosters (multi-roster support) + practice.roster_id

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-18

Adds many-to-many rosters so a coach can split players into separate teams and
private lessons. Every existing user gets a default "All Players" (team) roster
containing all of their current players, and every existing practice is bound to
that roster so attendance/groups keep working unchanged.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rosters",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="team"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("kind IN ('team', 'private')", name="roster_kind_valid"),
    )
    op.create_index("ix_rosters_user_id", "rosters", ["user_id"])

    op.create_table(
        "roster_players",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("roster_id", UUID(as_uuid=False), sa.ForeignKey("rosters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", UUID(as_uuid=False), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("roster_id", "player_id", name="roster_player_unique"),
    )
    op.create_index("ix_roster_players_roster_id", "roster_players", ["roster_id"])
    op.create_index("ix_roster_players_player_id", "roster_players", ["player_id"])

    op.add_column("practices", sa.Column("roster_id", UUID(as_uuid=False), nullable=True))
    op.create_index("ix_practices_roster_id", "practices", ["roster_id"])
    op.create_foreign_key(
        "practices_roster_id_fkey", "practices", "rosters", ["roster_id"], ["id"], ondelete="SET NULL"
    )

    # --- Backfill: one default roster per user, holding all their players ---
    op.execute(
        "INSERT INTO rosters (id, user_id, name, kind, sort_order, created_at) "
        "SELECT gen_random_uuid(), id, 'All Players', 'team', 0, now() FROM users"
    )
    # Each user has exactly one roster at this point, so this maps every player
    # (and every practice) to that user's default roster.
    op.execute(
        "INSERT INTO roster_players (id, roster_id, player_id, created_at) "
        "SELECT gen_random_uuid(), r.id, p.id, now() "
        "FROM players p JOIN rosters r ON r.user_id = p.user_id"
    )
    op.execute(
        "UPDATE practices SET roster_id = r.id "
        "FROM rosters r WHERE r.user_id = practices.user_id"
    )

    # Team + private on the same day must not collide: scope uniqueness by roster.
    op.drop_constraint("practice_user_date_unique", "practices", type_="unique")
    op.create_unique_constraint(
        "practice_user_date_roster_unique", "practices", ["user_id", "date", "roster_id"]
    )


def downgrade() -> None:
    op.drop_constraint("practice_user_date_roster_unique", "practices", type_="unique")
    op.create_unique_constraint("practice_user_date_unique", "practices", ["user_id", "date"])
    op.drop_constraint("practices_roster_id_fkey", "practices", type_="foreignkey")
    op.drop_index("ix_practices_roster_id", table_name="practices")
    op.drop_column("practices", "roster_id")
    op.drop_index("ix_roster_players_player_id", table_name="roster_players")
    op.drop_index("ix_roster_players_roster_id", table_name="roster_players")
    op.drop_table("roster_players")
    op.drop_index("ix_rosters_user_id", table_name="rosters")
    op.drop_table("rosters")

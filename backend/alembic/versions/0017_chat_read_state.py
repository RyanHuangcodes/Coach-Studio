"""chat read-state (unread counts)

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("players", sa.Column("coach_last_read_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("players", sa.Column("player_last_read_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("players", "player_last_read_at")
    op.drop_column("players", "coach_last_read_at")

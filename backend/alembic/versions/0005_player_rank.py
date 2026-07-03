"""add rank column to players

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("players", sa.Column("rank", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("players", "rank")

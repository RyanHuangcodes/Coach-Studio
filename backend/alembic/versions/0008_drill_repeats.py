"""add repeats column to drills

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("drills", sa.Column("repeats", sa.Integer(), nullable=False, server_default="1"))
    op.create_check_constraint("drill_repeats_range", "drills", "repeats >= 1 AND repeats <= 20")


def downgrade() -> None:
    op.drop_constraint("drill_repeats_range", "drills", type_="check")
    op.drop_column("drills", "repeats")

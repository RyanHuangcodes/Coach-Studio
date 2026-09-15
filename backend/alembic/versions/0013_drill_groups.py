"""add groups column to drills

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-21

"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("drills", sa.Column("groups", sa.Integer(), nullable=False, server_default="1"))
    op.create_check_constraint("drill_groups_range", "drills", "groups >= 1 AND groups <= 60")


def downgrade() -> None:
    op.drop_constraint("drill_groups_range", "drills", type_="check")
    op.drop_column("drills", "groups")

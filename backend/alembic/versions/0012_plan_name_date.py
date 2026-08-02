"""add optional name and session_date to plans

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-23

"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("name", sa.String(80), nullable=True))
    op.add_column("plans", sa.Column("session_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("plans", "session_date")
    op.drop_column("plans", "name")

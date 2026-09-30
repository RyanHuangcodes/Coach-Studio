"""assignment due dates

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assignments", sa.Column("due_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("assignments", "due_date")

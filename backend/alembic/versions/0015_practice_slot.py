"""practice session slot (morning/afternoon/night)

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-19

Lets a roster train more than once on the same day: each practice gets a `slot`
('day' by default, or 'morning'/'afternoon'/'night'), and uniqueness is scoped
per slot so the sessions keep separate attendance.
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "practices",
        sa.Column("slot", sa.String(length=12), nullable=False, server_default="day"),
    )
    op.drop_constraint("practice_user_date_roster_unique", "practices", type_="unique")
    op.create_unique_constraint(
        "practice_user_date_roster_slot_unique",
        "practices",
        ["user_id", "date", "roster_id", "slot"],
    )


def downgrade() -> None:
    op.drop_constraint("practice_user_date_roster_slot_unique", "practices", type_="unique")
    op.create_unique_constraint(
        "practice_user_date_roster_unique", "practices", ["user_id", "date", "roster_id"]
    )
    op.drop_column("practices", "slot")

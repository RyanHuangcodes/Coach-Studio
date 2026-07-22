"""normalize existing user emails to lowercase

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-22

New signups/logins normalize email to lowercase at the app layer; bring any
pre-existing rows into line so a coach who registered with mixed case can still
log in. Assumes no two existing rows collide when lowercased (true for this
dataset); if they did, the unique index would reject the update and flag it.
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET email = lower(trim(email)) WHERE email <> lower(trim(email))")


def downgrade() -> None:
    # Lowercasing is not reversible; nothing to undo.
    pass

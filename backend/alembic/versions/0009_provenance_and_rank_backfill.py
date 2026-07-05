"""drop plans.source_draft_id FK (self-defeating) and backfill NULL player ranks

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-05

"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The source draft is deleted in the same transaction that creates the plan,
    # so ON DELETE SET NULL wiped this column on every write. Keep the value as a
    # plain historical reference instead.
    op.drop_constraint("plans_source_draft_id_fkey", "plans", type_="foreignkey")

    # Players created before migration 0005 have rank NULL, which makes the
    # move-up/down endpoint a silent no-op (NULL swapped with NULL). Assign ranks
    # after any existing ranked players, ordered by creation time.
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   COALESCE(
                       (SELECT MAX(p2.rank) FROM players p2
                        WHERE p2.user_id = players.user_id AND p2.tier_id = players.tier_id),
                       0
                   )
                   + ROW_NUMBER() OVER (
                       PARTITION BY user_id, tier_id ORDER BY created_at
                   ) AS new_rank
            FROM players
            WHERE rank IS NULL AND tier_id IS NOT NULL
        )
        UPDATE players
        SET rank = ranked.new_rank
        FROM ranked
        WHERE players.id = ranked.id
        """
    )


def downgrade() -> None:
    op.create_foreign_key(
        "plans_source_draft_id_fkey",
        "plans",
        "drafts",
        ["source_draft_id"],
        ["id"],
        ondelete="SET NULL",
    )

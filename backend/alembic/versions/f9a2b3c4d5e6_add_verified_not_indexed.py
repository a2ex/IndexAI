"""add verified_not_indexed to urls

Revision ID: f9a2b3c4d5e6
Revises: e7f8a1b2c3d4
Create Date: 2025-02-09 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f9a2b3c4d5e6"
down_revision: Union[str, None] = "e7f8a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "urls",
        sa.Column("verified_not_indexed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    # Backfill: URLs that are currently indexed AND had check_count >= 2
    # means they were checked at least once as not-indexed before becoming indexed
    op.execute(
        "UPDATE urls SET verified_not_indexed = true "
        "WHERE status = 'indexed' AND pre_indexed = false AND check_count >= 2"
    )
    # Also backfill URLs currently in not_indexed status (they were verified as not indexed)
    op.execute(
        "UPDATE urls SET verified_not_indexed = true WHERE status = 'not_indexed'"
    )


def downgrade() -> None:
    op.drop_column("urls", "verified_not_indexed")

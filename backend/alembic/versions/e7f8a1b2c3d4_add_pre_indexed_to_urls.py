"""add pre_indexed to urls

Revision ID: e7f8a1b2c3d4
Revises: dc931a4ca0b4
Create Date: 2025-02-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7f8a1b2c3d4"
down_revision: Union[str, None] = "dc931a4ca0b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "urls",
        sa.Column("pre_indexed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    # Backfill: URLs that were already indexed at pre-check time
    # (credit_refunded=true AND status=indexed only happens in _mark_already_indexed)
    op.execute(
        "UPDATE urls SET pre_indexed = true WHERE status = 'indexed' AND credit_refunded = true"
    )


def downgrade() -> None:
    op.drop_column("urls", "pre_indexed")

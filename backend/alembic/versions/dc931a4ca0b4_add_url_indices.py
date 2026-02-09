"""add_url_indices

Revision ID: dc931a4ca0b4
Revises: a1b2c3d4e5f6
Create Date: 2026-02-09 09:49:08.022941

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'dc931a4ca0b4'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_urls_project_status', 'urls', ['project_id', 'status'])
    op.create_index('idx_urls_status', 'urls', ['status'])
    op.create_index('idx_urls_submitted_at', 'urls', ['submitted_at'])
    op.create_index('idx_urls_credit_check', 'urls', ['credit_debited', 'is_indexed', 'submitted_at'])


def downgrade() -> None:
    op.drop_index('idx_urls_credit_check', table_name='urls')
    op.drop_index('idx_urls_submitted_at', table_name='urls')
    op.drop_index('idx_urls_status', table_name='urls')
    op.drop_index('idx_urls_project_status', table_name='urls')

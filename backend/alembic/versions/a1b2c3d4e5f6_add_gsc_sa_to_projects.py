"""add gsc_service_account_id to projects

Revision ID: a1b2c3d4e5f6
Revises: b9a6ccbe9713
Create Date: 2026-02-08 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b9a6ccbe9713'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'projects',
        sa.Column('gsc_service_account_id', sa.Uuid(), sa.ForeignKey('service_accounts.id'), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('projects', 'gsc_service_account_id')

"""add_notification_settings

Revision ID: af72786bbb09
Revises: 945912931bc0
Create Date: 2026-02-07 22:53:57.347726

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af72786bbb09'
down_revision: Union[str, None] = '945912931bc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notification_settings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('webhook_url', sa.String(), nullable=True),
        sa.Column('webhook_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('email_digest_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('email_digest_address', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('notification_settings')

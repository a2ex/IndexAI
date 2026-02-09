"""add imported_sitemaps table

Revision ID: b9a6ccbe9713
Revises: be3f32300bd3
Create Date: 2026-02-08 02:32:19.957432

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9a6ccbe9713'
down_revision: Union[str, None] = 'be3f32300bd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'imported_sitemaps',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('sitemap_url', sa.String(), nullable=False),
        sa.Column('urls_imported', sa.Integer(), server_default='0'),
        sa.Column('imported_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('imported_sitemaps')

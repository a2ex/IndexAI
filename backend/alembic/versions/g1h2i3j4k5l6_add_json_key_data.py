"""add json_key_data to service_accounts

Revision ID: g1h2i3j4k5l6
Revises: f9a2b3c4d5e6
Create Date: 2026-02-09 00:00:01.000000

"""
from typing import Sequence, Union
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "f9a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add json_key_data column
    op.add_column("service_accounts", sa.Column("json_key_data", sa.Text(), nullable=True))

    # Make json_key_path nullable
    op.alter_column("service_accounts", "json_key_path", existing_type=sa.String(), nullable=True)

    # Backfill: read existing JSON files and store content in json_key_data
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, json_key_path FROM service_accounts WHERE json_key_path IS NOT NULL")
    ).fetchall()

    for row in rows:
        sa_id, key_path = row
        if key_path:
            path = Path(key_path)
            if path.exists():
                try:
                    content = path.read_text()
                    # Validate it's valid JSON
                    json.loads(content)
                    conn.execute(
                        sa.text("UPDATE service_accounts SET json_key_data = :data WHERE id = :id"),
                        {"data": content, "id": sa_id},
                    )
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Warning: Could not read {key_path}: {e}")


def downgrade() -> None:
    op.drop_column("service_accounts", "json_key_data")
    op.alter_column("service_accounts", "json_key_path", existing_type=sa.String(), nullable=False)

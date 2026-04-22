"""Add country_full to authors.

Revision ID: u8v9w0x1y2zc
Revises: t7u8v9w0x1yb
Create Date: 2026-04-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "u8v9w0x1y2zc"
down_revision: Union[str, Sequence[str], None] = "t7u8v9w0x1yb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("authors", sa.Column("country_full", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("authors", "country_full")

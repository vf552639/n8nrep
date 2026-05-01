"""Add hide_author_geo to blueprint_pages.

Revision ID: y1z2a3b4c5d6
Revises: x9y8z7w6v5u4
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "y1z2a3b4c5d6"
down_revision: str | Sequence[str] | None = "x9y8z7w6v5u4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "blueprint_pages",
        sa.Column("hide_author_geo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("blueprint_pages", "hide_author_geo", server_default=None)


def downgrade() -> None:
    op.drop_column("blueprint_pages", "hide_author_geo")

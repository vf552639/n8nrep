"""Add competitor_urls JSONB to site_projects.

Revision ID: v0a1b2c3d4e5
Revises: u8v9w0x1y2zc
Create Date: 2026-04-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "v0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "u8v9w0x1y2zc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "site_projects",
        sa.Column(
            "competitor_urls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="User-provided competitor URLs (merged into SERP urls before scraping)",
        ),
    )


def downgrade() -> None:
    op.drop_column("site_projects", "competitor_urls")

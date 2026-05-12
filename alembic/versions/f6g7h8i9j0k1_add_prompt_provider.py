"""add provider column to prompts (desktop).

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-05-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6g7h8i9j0k1"
down_revision: str | Sequence[str] | None = "e5f6g7h8i9j0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "prompts",
        sa.Column(
            "provider",
            sa.String(20),
            nullable=False,
            server_default="openrouter",
        ),
    )


def downgrade() -> None:
    op.drop_column("prompts", "provider")

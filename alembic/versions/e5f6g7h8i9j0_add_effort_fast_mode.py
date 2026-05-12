"""add effort and fast_mode to prompts (desktop).

Revision ID: e5f6g7h8i9j0
Revises: d0e1s2k3t0p5
Create Date: 2026-05-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6g7h8i9j0"
down_revision: str | Sequence[str] | None = "d0e1s2k3t0p5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "prompts",
        sa.Column("effort", sa.String(20), nullable=False, server_default="low"),
    )
    op.add_column(
        "prompts",
        sa.Column("fast_mode", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("prompts", "fast_mode")
    op.drop_column("prompts", "effort")

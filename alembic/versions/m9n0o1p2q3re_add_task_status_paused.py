"""add_task_status_paused

Revision ID: m9n0o1p2q3re
Revises: l6m7n8o9p0qc
Create Date: 2026-04-13

"""
from typing import Sequence, Union

from alembic import op

revision: str = "m9n0o1p2q3re"
down_revision: Union[str, Sequence[str], None] = "l6m7n8o9p0qc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'paused'")


def downgrade() -> None:
    # PostgreSQL cannot remove enum values safely; no-op.
    pass

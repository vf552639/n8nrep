"""add started_at completed_at logs to site_projects

Revision ID: f1a2b3c4d5e7
Revises: e7f8a9b0c1d2
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f1a2b3c4d5e7"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("site_projects", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("site_projects", sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "site_projects",
        sa.Column(
            "logs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("site_projects", "logs")
    op.drop_column("site_projects", "completed_at")
    op.drop_column("site_projects", "started_at")

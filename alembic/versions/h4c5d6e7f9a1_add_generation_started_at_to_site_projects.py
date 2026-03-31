"""add generation_started_at to site_projects

Revision ID: h4c5d6e7f9a1
Revises: g2b3c4d5e6f8
Create Date: 2026-03-31 12:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "h4c5d6e7f9a1"
down_revision = "g2b3c4d5e6f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site_projects",
        sa.Column("generation_started_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("site_projects", "generation_started_at")

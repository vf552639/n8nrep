"""add project_keywords JSONB to site_projects

Revision ID: j4k5l6m7n8oa
Revises: i3d4e5f6a7b8
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "j4k5l6m7n8oa"
down_revision = "i3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site_projects",
        sa.Column(
            "project_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("site_projects", "project_keywords")

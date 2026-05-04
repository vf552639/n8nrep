"""site_projects: nullable fields for draft + target_site string.

Revision ID: z2a3b4c5d6e7
Revises: y1z2a3b4c5d6
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "z2a3b4c5d6e7"
down_revision: str | Sequence[str] | None = "y1z2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "site_projects",
        "blueprint_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "site_projects",
        "site_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "site_projects",
        "seed_keyword",
        existing_type=sa.String(length=500),
        nullable=True,
    )
    op.alter_column(
        "site_projects",
        "country",
        existing_type=sa.String(length=10),
        nullable=True,
    )
    op.alter_column(
        "site_projects",
        "language",
        existing_type=sa.String(length=10),
        nullable=True,
    )
    op.add_column(
        "site_projects",
        sa.Column(
            "target_site",
            sa.String(length=500),
            nullable=True,
            comment="Target site (site UUID or domain) while status=draft; resolved to site_id at launch",
        ),
    )


def downgrade() -> None:
    # Fails if any row has NULL in tightened columns or orphan draft rows.
    op.drop_column("site_projects", "target_site")
    op.alter_column("site_projects", "language", existing_type=sa.String(length=10), nullable=False)
    op.alter_column("site_projects", "country", existing_type=sa.String(length=10), nullable=False)
    op.alter_column("site_projects", "seed_keyword", existing_type=sa.String(length=500), nullable=False)
    op.alter_column(
        "site_projects",
        "site_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "site_projects",
        "blueprint_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

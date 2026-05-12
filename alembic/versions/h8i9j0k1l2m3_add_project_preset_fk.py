"""add site_projects.prompt_preset_id FK.

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-05-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "h8i9j0k1l2m3"
down_revision: str | Sequence[str] | None = "g7h8i9j0k1l2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("site_projects") as batch:
        batch.add_column(sa.Column("prompt_preset_id", sa.Uuid(as_uuid=True), nullable=True))
        batch.create_foreign_key(
            "fk_site_projects_prompt_preset",
            "prompt_presets",
            ["prompt_preset_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("site_projects") as batch:
        batch.drop_constraint("fk_site_projects_prompt_preset", type_="foreignkey")
        batch.drop_column("prompt_preset_id")

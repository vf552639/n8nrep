"""add prompt_presets and prompt_preset_items tables.

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2026-05-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g7h8i9j0k1l2"
down_revision: str | Sequence[str] | None = "f6g7h8i9j0k1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prompt_presets",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "prompt_preset_items",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("preset_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("prompt_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["preset_id"], ["prompt_presets.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["prompt_id"], ["prompts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("preset_id", "agent_name", name="uq_preset_agent"),
    )
    op.create_index("ix_preset_items_agent", "prompt_preset_items", ["agent_name"])


def downgrade() -> None:
    op.drop_index("ix_preset_items_agent", table_name="prompt_preset_items")
    op.drop_table("prompt_preset_items")
    op.drop_table("prompt_presets")

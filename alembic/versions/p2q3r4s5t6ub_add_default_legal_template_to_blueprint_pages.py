"""Add default_legal_template_id to blueprint_pages

Revision ID: p2q3r4s5t6ub
Revises: n1o2p3q4r5sa
Create Date: 2026-04-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "p2q3r4s5t6ub"
down_revision: Union[str, Sequence[str], None] = "n1o2p3q4r5sa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "blueprint_pages",
        sa.Column(
            "default_legal_template_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_bp_page_default_legal_tpl",
        "blueprint_pages",
        "legal_page_templates",
        ["default_legal_template_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_bp_page_default_legal_tpl", "blueprint_pages", type_="foreignkey")
    op.drop_column("blueprint_pages", "default_legal_template_id")

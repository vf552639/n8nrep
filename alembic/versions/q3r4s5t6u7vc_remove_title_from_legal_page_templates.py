"""remove title from legal_page_templates

Revision ID: q3r4s5t6u7vc
Revises: p2q3r4s5t6ub
Create Date: 2026-04-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "q3r4s5t6u7vc"
down_revision: Union[str, Sequence[str], None] = "p2q3r4s5t6ub"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("legal_page_templates", "title")


def downgrade() -> None:
    op.add_column(
        "legal_page_templates",
        sa.Column(
            "title",
            sa.String(length=300),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("legal_page_templates", "title", server_default=None)

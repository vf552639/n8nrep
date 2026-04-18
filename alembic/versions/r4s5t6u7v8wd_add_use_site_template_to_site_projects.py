"""add use_site_template to site_projects

Revision ID: r4s5t6u7v8wd
Revises: q3r4s5t6u7vc
Create Date: 2026-04-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "r4s5t6u7v8wd"
down_revision: Union[str, Sequence[str], None] = "q3r4s5t6u7vc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "site_projects",
        sa.Column(
            "use_site_template",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Use site HTML template wrapper for generated pages",
        ),
    )


def downgrade() -> None:
    op.drop_column("site_projects", "use_site_template")

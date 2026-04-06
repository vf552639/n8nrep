"""Add pipeline_preset and pipeline_steps_custom to blueprint_pages

Revision ID: l6m7n8o9p0qc
Revises: k5m6n7o8p9qb
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "l6m7n8o9p0qc"
down_revision = "k5m6n7o8p9qb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "blueprint_pages",
        sa.Column(
            "pipeline_preset",
            sa.String(20),
            nullable=False,
            server_default="full",
        ),
    )
    op.add_column(
        "blueprint_pages",
        sa.Column("pipeline_steps_custom", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.execute(
        """
        UPDATE blueprint_pages
        SET pipeline_preset = 'legal'
        WHERE use_serp = false
          AND page_type IN (
            'privacy_policy', 'terms_and_conditions',
            'cookie_policy', 'responsible_gambling'
          )
        """
    )
    op.execute(
        """
        UPDATE blueprint_pages
        SET pipeline_preset = 'about'
        WHERE use_serp = false
          AND (page_type = 'about_us' OR page_slug ILIKE '%about%')
          AND pipeline_preset = 'full'
        """
    )
    op.execute(
        """
        UPDATE blueprint_pages
        SET pipeline_preset = 'category'
        WHERE use_serp = false
          AND pipeline_preset = 'full'
        """
    )


def downgrade() -> None:
    op.drop_column("blueprint_pages", "pipeline_steps_custom")
    op.drop_column("blueprint_pages", "pipeline_preset")

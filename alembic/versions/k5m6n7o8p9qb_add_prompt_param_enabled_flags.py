"""add *_enabled flags to prompts for Model Settings

Revision ID: k5m6n7o8p9qb
Revises: j4k5l6m7n8oa
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa

revision = "k5m6n7o8p9qb"
down_revision = "j4k5l6m7n8oa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prompts",
        sa.Column("max_tokens_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "prompts",
        sa.Column("temperature_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "prompts",
        sa.Column("frequency_penalty_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "prompts",
        sa.Column("presence_penalty_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "prompts",
        sa.Column("top_p_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.execute(
        """
        UPDATE prompts SET
          max_tokens_enabled = (max_tokens IS NOT NULL AND max_tokens > 0),
          temperature_enabled = (
            temperature IS NOT NULL AND abs(temperature - 0.7) > 0.0001
          ),
          frequency_penalty_enabled = (
            frequency_penalty IS NOT NULL AND abs(frequency_penalty) > 0.0001
          ),
          presence_penalty_enabled = (
            presence_penalty IS NOT NULL AND abs(presence_penalty) > 0.0001
          ),
          top_p_enabled = (
            top_p IS NOT NULL AND abs(top_p - 1.0) > 0.0001
          )
        """
    )

    op.alter_column("prompts", "max_tokens_enabled", server_default=None)
    op.alter_column("prompts", "temperature_enabled", server_default=None)
    op.alter_column("prompts", "frequency_penalty_enabled", server_default=None)
    op.alter_column("prompts", "presence_penalty_enabled", server_default=None)
    op.alter_column("prompts", "top_p_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("prompts", "top_p_enabled")
    op.drop_column("prompts", "presence_penalty_enabled")
    op.drop_column("prompts", "frequency_penalty_enabled")
    op.drop_column("prompts", "temperature_enabled")
    op.drop_column("prompts", "max_tokens_enabled")

"""add_serp_config_to_tasks

Revision ID: c8f9a0b1d2e3
Revises: a73a75b2050a
Create Date: 2026-03-25 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c8f9a0b1d2e3'
down_revision: Union[str, Sequence[str], None] = '405ed8482003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('serp_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'serp_config')

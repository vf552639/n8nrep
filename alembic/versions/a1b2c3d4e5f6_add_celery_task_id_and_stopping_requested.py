"""Add celery_task_id and stopping_requested to site_projects

Revision ID: a1b2c3d4e5f6
Revises: 66e7b7bc01f0
Create Date: 2026-03-10 16:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '66e7b7bc01f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('site_projects', sa.Column('celery_task_id', sa.String(length=255), nullable=True,
                                              comment='Celery task ID для отладки'))
    op.add_column('site_projects', sa.Column('stopping_requested', sa.Boolean(), nullable=True,
                                              server_default='false',
                                              comment='Флаг запроса остановки'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('site_projects', 'stopping_requested')
    op.drop_column('site_projects', 'celery_task_id')

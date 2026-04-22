"""Add celery_task_id to tasks for revoke on stale/force-fail.

Revision ID: x9y8z7w6v5u4
Revises: v0a1b2c3d4e5
Create Date: 2026-04-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "x9y8z7w6v5u4"
down_revision: str | Sequence[str] | None = "v0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("celery_task_id", sa.String(length=64), nullable=True))
    op.create_index("ix_tasks_celery_task_id", "tasks", ["celery_task_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_celery_task_id", table_name="tasks")
    op.drop_column("tasks", "celery_task_id")

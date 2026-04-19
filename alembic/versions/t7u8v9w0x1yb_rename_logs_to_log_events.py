"""Rename JSONB logs -> log_events on tasks and site_projects.

Revision ID: t7u8v9w0x1yb
Revises: s6t7u8v9w0xe
Create Date: 2026-04-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "t7u8v9w0x1yb"
down_revision: Union[str, Sequence[str], None] = "s6t7u8v9w0xe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "log_events",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )
    op.add_column(
        "site_projects",
        sa.Column(
            "log_events",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )

    op.execute(
        """
        UPDATE tasks SET log_events = CASE
            WHEN logs IS NULL OR jsonb_typeof(logs) <> 'array' THEN '[]'::jsonb
            WHEN jsonb_array_length(logs) <= 500 THEN logs
            ELSE (
                SELECT COALESCE(jsonb_agg(elem ORDER BY ord), '[]'::jsonb)
                FROM (
                    SELECT elem, ord
                    FROM jsonb_array_elements(tasks.logs) WITH ORDINALITY AS t(elem, ord)
                ) sub
                WHERE ord > jsonb_array_length(tasks.logs) - 500
            )
        END
        """
    )
    op.execute(
        """
        UPDATE site_projects SET log_events = CASE
            WHEN logs IS NULL OR jsonb_typeof(logs) <> 'array' THEN '[]'::jsonb
            WHEN jsonb_array_length(logs) <= 500 THEN logs
            ELSE (
                SELECT COALESCE(jsonb_agg(elem ORDER BY ord), '[]'::jsonb)
                FROM (
                    SELECT elem, ord
                    FROM jsonb_array_elements(site_projects.logs) WITH ORDINALITY AS t(elem, ord)
                ) sub
                WHERE ord > jsonb_array_length(site_projects.logs) - 500
            )
        END
        """
    )

    op.drop_column("tasks", "logs")
    op.drop_column("site_projects", "logs")


def downgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("logs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "site_projects",
        sa.Column("logs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute("UPDATE tasks SET logs = log_events")
    op.execute("UPDATE site_projects SET logs = log_events")
    op.drop_column("tasks", "log_events")
    op.drop_column("site_projects", "log_events")

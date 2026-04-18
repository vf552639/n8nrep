"""Normalize language casing on authors and sites (INITCAP/TRIM).

Revision ID: s6t7u8v9w0xe
Revises: r4s5t6u7v8wd
Create Date: 2026-04-18
"""

from typing import Sequence, Union

from alembic import op

revision: str = "s6t7u8v9w0xe"
down_revision: Union[str, Sequence[str], None] = "r4s5t6u7v8wd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE authors
        SET language = INITCAP(TRIM(language))
        WHERE language IS NOT NULL AND BTRIM(language) <> '';
        """
    )
    op.execute(
        """
        UPDATE sites
        SET language = INITCAP(TRIM(language))
        WHERE language IS NOT NULL AND BTRIM(language) <> '';
        """
    )


def downgrade() -> None:
    # Irreversible data normalization
    pass

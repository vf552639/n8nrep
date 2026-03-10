"""merge_heads_stop_feature

Revision ID: 37ef8f986c2b
Revises: 2a97225f2970, a1b2c3d4e5f6
Create Date: 2026-03-10 15:09:34.681114

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37ef8f986c2b'
down_revision: Union[str, Sequence[str], None] = ('2a97225f2970', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

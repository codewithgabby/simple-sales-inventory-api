"""add performance indexes

Revision ID: fad63f31015e
Revises: 5abcf9b9aa5f
Create Date: 2026-02-17 13:41:29.279904

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fad63f31015e'
down_revision: Union[str, Sequence[str], None] = '5abcf9b9aa5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

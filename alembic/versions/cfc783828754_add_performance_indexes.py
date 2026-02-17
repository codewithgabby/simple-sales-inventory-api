"""add performance indexes

Revision ID: cfc783828754
Revises: fad63f31015e
Create Date: 2026-02-17 14:45:26.839262

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfc783828754'
down_revision: Union[str, Sequence[str], None] = 'fad63f31015e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

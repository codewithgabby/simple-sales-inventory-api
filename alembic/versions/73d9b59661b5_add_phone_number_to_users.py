"""add phone number to users

Revision ID: 73d9b59661b5
Revises: 04240418795b
Create Date: 2026-03-11
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "73d9b59661b5"
down_revision: Union[str, Sequence[str], None] = "04240418795b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("phone_number", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "phone_number")
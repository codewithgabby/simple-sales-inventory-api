"""add_missing_production_indexes

Revision ID: 743c06a3e7e6
Revises: cfc783828754
Create Date: 2026-02-20 14:55:20.033567
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '743c06a3e7e6'
down_revision: Union[str, Sequence[str], None] = 'cfc783828754'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # PRODUCTS
    op.create_index(
        "ix_products_business_id",
        "products",
        ["business_id"],
        unique=False,
    )

    # INVENTORY
    op.create_index(
        "ix_inventory_business_id",
        "inventory",
        ["business_id"],
        unique=False,
    )

    # SALES
    op.create_index(
        "ix_sales_created_at",
        "sales",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_sales_business_id_created_at",
        "sales",
        ["business_id", "created_at"],
        unique=False,
    )

    # SALE ITEMS
    op.create_index(
        "ix_sale_items_sale_id",
        "sale_items",
        ["sale_id"],
        unique=False,
    )

    op.create_index(
        "ix_sale_items_product_id",
        "sale_items",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index("ix_sale_items_product_id", table_name="sale_items")
    op.drop_index("ix_sale_items_sale_id", table_name="sale_items")
    op.drop_index("ix_sales_business_id_created_at", table_name="sales")
    op.drop_index("ix_sales_created_at", table_name="sales")
    op.drop_index("ix_inventory_business_id", table_name="inventory")
    op.drop_index("ix_products_business_id", table_name="products")
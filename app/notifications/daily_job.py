from app.utils.phone import format_nigerian_phone

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models.users import User
from app.models.products import Product
from app.models.inventory import Inventory
from app.models.sales import Sale
from app.models.sale_items import SaleItem
from app.core.subscription import get_active_subscription
from app.notifications.sms_service import send_sms


def run_daily_notifications():

    db: Session = SessionLocal()

    today = datetime.now(timezone.utc).date()

    users = db.query(User).all()

    for user in users:

        if not user.phone_number:
            continue

        subscription = get_active_subscription(db, user.business_id)

        if not subscription:
            continue

        # SALES TOTAL
        sales_total = (
            db.query(func.coalesce(func.sum(Sale.total_amount), 0))
            .filter(
                Sale.business_id == user.business_id,
                func.date(Sale.created_at) == today
            )
            .scalar()
        )

        # ORDER COUNT
        orders = (
            db.query(func.count(Sale.id))
            .filter(
                Sale.business_id == user.business_id,
                func.date(Sale.created_at) == today
            )
            .scalar()
        )

        # PROFIT
        cost_total = (
            db.query(func.coalesce(func.sum(Product.cost_price * SaleItem.quantity), 0))
            .join(SaleItem, SaleItem.product_id == Product.id)
            .join(Sale, SaleItem.sale_id == Sale.id)
            .filter(
                Sale.business_id == user.business_id,
                func.date(Sale.created_at) == today
            )
            .scalar()
        )

        profit = sales_total - cost_total

        # LOW STOCK
        low_stock = (
            db.query(Product.name, Inventory.quantity_available)
            .join(Inventory, Inventory.product_id == Product.id)
            .filter(
                Product.business_id == user.business_id,
                Inventory.quantity_available <= Inventory.low_stock_threshold
            )
            .limit(2)
            .all()
        )

        low_stock_text = ""

        if low_stock:
            items = [f"{p.name}({p.quantity_available})" for p in low_stock]
            low_stock_text = "Low:" + ",".join(items)

        message = (
            f"Saleszy Report "
            f"Sales ₦{sales_total} "
            f"Profit ₦{profit} "
            f"Orders {orders} "
            f"{low_stock_text}"
        )

        phone = format_nigerian_phone(user.phone_number)
        send_sms(phone, message)

    db.close()
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import get_current_user
from app.models.products import Product
from app.models.inventory import Inventory
from app.models.sales import Sale
from app.core.subscription import get_active_subscription

from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    subscription = get_active_subscription(db, current_user.business_id)

    # PRODUCTS
    products = db.query(Product).filter(
        Product.business_id == current_user.business_id
    ).all()

    # INVENTORY
    inventory = db.query(Inventory).filter(
        Inventory.product_id.in_([p.id for p in products])
    ).all()

    # SALES (respect subscription)
    query = db.query(Sale).filter(
        Sale.business_id == current_user.business_id
    )

    if not subscription:
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=6)
        query = query.filter(Sale.created_at >= seven_days_ago)

    sales = query.all()

    return {
        "products": products,
        "inventory": inventory,
        "sales": sales,
    }
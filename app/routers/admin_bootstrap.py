# app/routers/admin_bootstrap.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.users import User
from app.core.config import settings

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.post("/make-admin")
def make_admin(
    email: str,
    db: Session = Depends(get_db),
):
    """
    TEMPORARY ENDPOINT
    Makes a user admin by email.
    Should be removed after use.
    """

    # Safety check: only allow in development
    """ if settings.ENV != "development":
        raise HTTPException(status_code=403, detail="Not allowed in production") """

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = True
    db.commit()

    return {"message": f"{email} is now admin"}
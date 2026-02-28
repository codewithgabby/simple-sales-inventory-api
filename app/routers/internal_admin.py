from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.users import User
from app.core.config import settings

router = APIRouter(prefix="/internal", tags=["Internal"])

@router.post("/promote-admin")
def promote_admin(
    email: str,
    secret: str,
    db: Session = Depends(get_db),
):
    # Protect this route with a secret key
    if secret != settings.INTERNAL_ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = True
    db.commit()

    return {"message": f"{email} promoted to admin"}
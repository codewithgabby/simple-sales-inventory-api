from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta, timezone
import secrets
import logging

from app.utils.phone import format_nigerian_phone
from app.database import get_db
from app.models.business import Business
from app.models.users import User
from app.schemas.user import UserCreate, PhoneUpdate, UserProfileResponse
from app.core.hashing import hash_password, verify_password
from app.core.jwt import create_access_token
from app.core.rate_limiter import limiter
from app.core.config import settings
from app.core.email import send_password_reset_email
from app.core.current_user import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

COMMON_PASSWORDS = {
    "password",
    "password123",
    "12345678",
    "qwerty123",
    "admin123",
}

# ---------------- SIGNUP ----------------
@router.post("/signup", status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
def signup(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    raw_password = user_data.password.lower()

    if raw_password in COMMON_PASSWORDS:
        raise HTTPException(
            status_code=400,
            detail="Password is too common. Please choose a stronger password.",
        )

    if user_data.password.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Password cannot be numbers only.",
        )

    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=409, detail="Email already exists")

    if db.query(Business).filter(Business.name == user_data.business_name).first():
        raise HTTPException(status_code=409, detail="Business name already exists")

    # Format phone number
    formatted_phone = format_nigerian_phone(user_data.phone_number)

    # Check if phone number already exists
    existing_phone = (
        db.query(User)
        .filter(User.phone_number == formatted_phone)
        .first()
    )

    if existing_phone:
        raise HTTPException(
            status_code=409,
            detail="Phone number already used by another business"
        )

    try:
        business = Business(name=user_data.business_name)
        db.add(business)
        db.flush()

        user = User(
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            business_id=business.id,
            phone_number=formatted_phone,
        )

        db.add(user)
        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create account")

    return {"message": "Account created successfully. Please login."}

# ---------------- LOGIN (TOKEN-BASED) ----------------
@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT token with user ID, business ID, and admin status
    token = create_access_token(
        data={"sub": str(user.id), "business_id": user.business_id, "is_admin": user.is_admin}
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ---------------- LOGOUT ----------------
@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}


# ---------------- FORGOT PASSWORD ----------------
@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()

    if user:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_password(raw_token)

        user.reset_token_hash = token_hash
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )

        db.commit()

        reset_link = f"{settings.FRONTEND_RESET_URL}?token={raw_token}"
    try:    
        send_password_reset_email(user.email, reset_link)
    except Exception as e:
        # Log error but don't crash endpoint
        logger.error(f"Failed to send password reset email: {str(e)}")
        

    return {"message": "If the email exists, a reset link has been sent."}


# ---------------- RESET PASSWORD ----------------
@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(
    request: Request,
    token: str,
    new_password: str,
    db: Session = Depends(get_db),
):
    users = db.query(User).filter(User.reset_token_expires_at.isnot(None)).all()

    matched_user = None
    
    # Iterate through users with valid reset tokens to find a match
    for u in users:
        if (
            u.reset_token_expires_at
            and u.reset_token_expires_at > datetime.utcnow()
            and verify_password(token, u.reset_token_hash)
        ):
            matched_user = u
            break

    if not matched_user:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token",
        )

    matched_user.password_hash = hash_password(new_password)
    matched_user.reset_token_hash = None
    matched_user.reset_token_expires_at = None

    db.commit()

    return {"message": "Password reset successful. Please login."}


# ---------------- UPDATE PHONE NUMBER ----------------
@router.put("/phone")
@limiter.limit("5/minute")
def update_phone_number(
    request: Request,
    data: PhoneUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    formatted_phone = format_nigerian_phone(data.phone_number)

    # Check if phone number already belongs to another business
    existing_user = (
        db.query(User)
        .filter(User.phone_number == formatted_phone, User.id != current_user.id)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Phone number already used by another business"
        )

    current_user.phone_number = formatted_phone

    db.commit()

    return {
        "message": "Phone number updated successfully",
        "phone_number": formatted_phone
    }

# ---------------- GET USER PROFILE ----------------
@router.get("/me", response_model=UserProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
):

    return {
        "email": current_user.email,
        "business_name": current_user.business.name,
        "phone_number": current_user.phone_number,
        "created_at": current_user.created_at
    }

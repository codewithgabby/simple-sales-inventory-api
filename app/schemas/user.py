from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=72, description="Plain password (will be hashed). Minimum 8 characters.")
    business_name: str = Field(..., min_length=2, max_length=100, description="Name of the business the user is associated with")
    phone_number: str = Field(..., min_length=10, max_length=15, description="User's phone number for SMS notifications")

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PhoneUpdate(BaseModel):
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="Phone number for SMS notifications"
    )


class UserProfileResponse(BaseModel):
    email: EmailStr
    business_name: str
    phone_number: str | None
    created_at: datetime

    class Config:
        from_attributes = True
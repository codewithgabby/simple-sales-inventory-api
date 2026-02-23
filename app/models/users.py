# app/models/users.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    business_id = Column(
        Integer, 
        ForeignKey("businesses.id"), 
        nullable=False,
    )
    
    # Admin flag to differentiate between regular users and business owners
    is_admin = Column(Boolean, default=False, nullable=False)

    reset_token_hash = Column(String, nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    business = relationship("Business")
    

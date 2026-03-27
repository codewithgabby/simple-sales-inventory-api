# app/models/business.py

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Date
from sqlalchemy.sql import func
from datetime import date

from app.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    is_suspended = Column(Boolean, default=False, nullable=False)
    
    # Streak tracking fields
    last_sale_date = Column(Date, nullable=True)
    current_streak = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
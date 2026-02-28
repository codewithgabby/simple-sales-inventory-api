# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    # App
    ENV: str = "development"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str
    ALGORITHM: Literal["HS256"] = "HS512"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str

    # Paystack
    PAYSTACK_SECRET_KEY: str | None = None

    # Email (Resend)
    RESEND_API_KEY: str
    RESEND_FROM_EMAIL: str

    # Password reset
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # Frontend
    FRONTEND_RESET_URL: str

    INTERNAL_ADMIN_SECRET: str



    model_config = SettingsConfigDict(
        env_file=".env",
        extra="forbid",  
    )


settings = Settings()

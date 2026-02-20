# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    ENV: str = "development"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
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



    model_config = SettingsConfigDict(
        env_file=".env",
        extra="forbid",  
    )


settings = Settings()

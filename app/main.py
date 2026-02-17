# Main application file

from fastapi.middleware.cors import CORSMiddleware
import os
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limiter import limiter

from fastapi import FastAPI
from app.database import engine, Base
from app import models
from app.routers import auth, products, inventory, sales, reports, exports, payments, webhooks

app = FastAPI(
    title="Simple Sales & Inventory API",
    description="Backend system for small vendors to track sales and inventory",
    version="1.0.0"
)

# CORS for token-based auth (no cookies needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://simplesales-web.netlify.app",
    ],
    allow_credentials=False,  # no cookies now
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(sales.router)
app.include_router(reports.router)
app.include_router(exports.router)
app.include_router(payments.router)
app.include_router(webhooks.router)


@app.get("/")
def root():
    return {
        "message": "Simple Sales & Inventory API is running"
    }


if os.getenv("BOOTSTRAP_DB") == "true":
    Base.metadata.create_all(bind=engine)

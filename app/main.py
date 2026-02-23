# Main application file



import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.database import engine, Base
from app.core.rate_limiter import limiter
from app.core.config import settings
from app.routers import (
    auth,
    products,
    inventory,
    sales,
    reports,
    exports,
    payments,
    webhooks,
    admin_bootstrap,
)      


# LOGGING CONFIGURATION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("app")


# APP INIT

app = FastAPI(
    title="Simple Sales & Inventory API",
    description="Backend system for small vendors to track sales and inventory",
    version="1.0.0",
)



# CORS (Token-based auth)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://simplesales-web.netlify.app",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# RATE LIMITING

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)


# REQUEST LOGGING MIDDLEWARE

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = round((time.time() - start_time) * 1000, 2)

    logger.info(
        f"{request.method} {request.url.path} "
        f"Status: {response.status_code} "
        f"Time: {duration}ms"
    )

    return response


# ROUTERS

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(sales.router)
app.include_router(reports.router)
app.include_router(exports.router)
app.include_router(payments.router)
app.include_router(webhooks.router)
app.include_router(admin_bootstrap.router)



# ROOT

@app.get("/")
def root():
    logger.info("Health check endpoint called")
    return {"message": "Simple Sales & Inventory API is running"}



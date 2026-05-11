# Main application file
from starlette.middleware.trustedhost import TrustedHostMiddleware
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.notifications.scheduler import start_scheduler
from app.database import engine, Base
from app.core.rate_limiter import limiter
from app.core.config import settings
from app.routers import (
    auth,
    products,
    product_units,
    inventory,
    sales,
    reports,
    insights,
    premium_intelligence,
    exports,
    payments,
    webhooks,
    admin, 
    subscription,
    notifications,
    dashboard,
    internal_admin
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

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "saleszy.com.ng",
        "saleszy.netlify.app",
        "api.saleszy.com.ng",
        "localhost",
        "127.0.0.1",
        "simple-sales-inventory-api-production.up.railway.app"
    ],
)

# CORS (Token-based auth)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://simplesales-web.netlify.app",
        "https://saleszy.com.ng",
        "https://saleszy.netlify.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(product_units.router)
app.include_router(inventory.router)
app.include_router(sales.router)
app.include_router(reports.router)
app.include_router(insights.router)
app.include_router(exports.router)
app.include_router(payments.router)
app.include_router(webhooks.router)
app.include_router(admin.router)
app.include_router(premium_intelligence.router)
app.include_router(subscription.router)
app.include_router(notifications.router)
app.include_router(dashboard.router)
app.include_router(internal_admin.router)

# ROOT

@app.get("/")
def root():
    logger.info("Health check endpoint called")
    return {"message": "Saleszy API is running"}

@app.on_event("startup")
def check_db_connection():
    try:
        with engine.connect() as connection:
            pass
        logger.info("Database connection successful")

        start_scheduler()

    except Exception as e:
        logger.error(f"Database connection failed")
        raise e    



@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

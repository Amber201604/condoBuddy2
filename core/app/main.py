"""CondoBuddy2 Core — Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.events import setup_events
from app.routers import (
    auth, users, work_orders, visitors, packages,
    access, cameras, sensors, lpr, notifications, facility_booking, webhooks
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="CondoBuddy2 Core API — Smart Community Platform",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Events
setup_events(app)

# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(work_orders.router, prefix="/api/v1")
app.include_router(visitors.router, prefix="/api/v1")
app.include_router(packages.router, prefix="/api/v1")
app.include_router(access.router, prefix="/api/v1")
app.include_router(cameras.router, prefix="/api/v1")
app.include_router(sensors.router, prefix="/api/v1")
app.include_router(lpr.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(facility_booking.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}

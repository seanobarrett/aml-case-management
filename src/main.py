"""
AML Case Management System - FastAPI Application.

Main application entry point with route configuration.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import (
    webhooks, cases, notifications, queue, templates,
    investigation, smr, onboarding_blocks, edd,
    holidays, dashboard, reports, users
)
from src.db.session import engine
from src.models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Create tables if they don't exist (development only)
    if os.getenv("ENVIRONMENT", "development") == "development":
        Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: Cleanup if needed
    pass


# Create FastAPI application
app = FastAPI(
    title="AML Case Management System",
    description="AUSTRAC AML/CTF compliance case management for Spriggy",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhooks.router)
app.include_router(cases.router)
app.include_router(notifications.router)
app.include_router(queue.router)
app.include_router(templates.router)
app.include_router(investigation.router)
app.include_router(smr.router)
app.include_router(onboarding_blocks.router)
app.include_router(edd.router)
app.include_router(holidays.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(users.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "aml-case-management"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "AML Case Management System",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }

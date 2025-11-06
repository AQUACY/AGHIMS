"""
Main FastAPI application
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api import (
    auth,
    patients,
    encounters,
    vitals,
    consultation,
    billing,
    claims,
    price_list,
    staff
)
from app.core.database import engine, Base

# Import all models to ensure they're registered with Base
import app.models  # This imports all models from __init__.py

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Hospital Management System API",
    description="OPD-focused HMS backend for quick billing and NHIA ClaimIT XML export",
    version="1.0.0"
)

# CORS middleware
# Get allowed origins from environment or use defaults
cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
# Filter out empty strings
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

# Default origins if not set via environment
if not cors_origins:
    cors_origins = [
        "http://localhost:9000",  # Development
        "http://localhost:3000",  # Development
        "http://127.0.0.1:9000",  # Development
        "http://127.0.0.1:3000",  # Development
        "http://localhost",  # Production (Apache)
        "http://localhost:8000",  # Production (direct backend access)
        "http://10.10.16.50",  # Production (Network IP)
        "http://10.10.16.50:8000",  # Production (Network IP with port)
        "http://10.10.16.50:9000",  # Production (Network IP dev server)
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(encounters.router, prefix="/api")
app.include_router(vitals.router, prefix="/api")
app.include_router(consultation.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(claims.router, prefix="/api")
app.include_router(price_list.router, prefix="/api")
app.include_router(staff.router, prefix="/api")

# Mount static files for lab result attachments
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Hospital Management System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


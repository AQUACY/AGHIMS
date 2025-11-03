"""
Main FastAPI application
"""
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:9000",
        "http://localhost:3000",
        "http://127.0.0.1:9000",
        "http://127.0.0.1:3000",
    ],  # Add frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


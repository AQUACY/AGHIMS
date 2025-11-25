"""
Main FastAPI application
"""
import os
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
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
    staff,
    lab_templates,
    analyzer,
    database_management,
    system,
    audit_logs
)
from app.core.database import engine, Base
import traceback

# Import all models to ensure they're registered with Base
import app.models  # This imports all models from __init__.py

# Create database tables (with error handling - don't crash if DB is temporarily unavailable)
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables verified/created successfully")
except Exception as e:
    print(f"WARNING: Could not create/verify database tables: {e}")
    print("This might be a connection issue. Server will start but database operations may fail.")
    print("Please check MySQL is running and configuration is correct.")
    import traceback
    traceback.print_exc()

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
        "http://10.10.16.50:9000/",  # Production (with trailing slash)
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Global exception handler to ensure CORS headers are included in error responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all exceptions and ensure CORS headers are included"""
    # Get the origin from the request
    origin = request.headers.get("origin")
    
    # Check if origin is in allowed origins
    if origin and origin in cors_origins:
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
        }
    else:
        # Default headers if origin not found or not in allowed list
        headers = {
            "Access-Control-Allow-Origin": cors_origins[0] if cors_origins else "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
        }
    
    # Log the error for debugging
    print(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    traceback.print_exc()
    
    # Return error response with CORS headers
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers=headers
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions and ensure CORS headers are included"""
    origin = request.headers.get("origin")
    
    if origin and origin in cors_origins:
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
        }
    else:
        headers = {
            "Access-Control-Allow-Origin": cors_origins[0] if cors_origins else "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
        }
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors and ensure CORS headers are included"""
    origin = request.headers.get("origin")
    
    if origin and origin in cors_origins:
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
        }
    else:
        headers = {
            "Access-Control-Allow-Origin": cors_origins[0] if cors_origins else "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
        }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
        headers=headers
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
app.include_router(lab_templates.router, prefix="/api")
app.include_router(analyzer.router, prefix="/api")
app.include_router(database_management.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(audit_logs.router, prefix="/api")

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
    try:
        from app.core.database import engine
        from sqlalchemy import text
        # Test database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "degraded", "database": "disconnected", "error": str(e)}


# Startup event: Start analyzer server if enabled
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    print("=" * 70)
    print("Application Startup - Initializing Analyzer Server...")
    print("=" * 70)
    try:
        from app.services.analyzer_server import start_analyzer_server
        from app.core.config import settings
        
        print(f"Analyzer enabled: {settings.ANALYZER_ENABLED}")
        if settings.ANALYZER_ENABLED:
            print("Starting analyzer server...")
            try:
                start_analyzer_server()
                print("Analyzer server startup initiated")
            except Exception as analyzer_error:
                print(f"WARNING: Analyzer server failed to start: {analyzer_error}")
                print("Application will continue without analyzer server")
                import traceback
                traceback.print_exc()
        else:
            print("Analyzer server is disabled (ANALYZER_ENABLED=false)")
    except Exception as e:
        print(f"ERROR: Failed to start analyzer server: {e}")
        print("Application will continue without analyzer server")
        import traceback
        traceback.print_exc()
    # Start backup scheduler
    try:
        from app.services.backup_scheduler import backup_scheduler
        backup_scheduler.start()
        print("Backup scheduler started")
    except ImportError as e:
        print(f"WARNING: Backup scheduler module not found: {e}")
        print("This is OK if APScheduler is not installed. Server will continue without scheduled backups.")
    except Exception as e:
        print(f"WARNING: Backup scheduler failed to start: {e}")
        print("Server will continue without scheduled backups.")
        import traceback
        traceback.print_exc()
    
    print("=" * 70)
    print("Application startup complete")
    print("=" * 70)


# Shutdown event: Stop analyzer server and backup scheduler
@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    print("Application Shutdown - Stopping Services...")
    
    # Stop analyzer server
    try:
        from app.services.analyzer_server import stop_analyzer_server
        stop_analyzer_server()
    except Exception as e:
        print(f"ERROR: Failed to stop analyzer server: {e}")
    
    # Stop backup scheduler
    try:
        from app.services.backup_scheduler import backup_scheduler
        backup_scheduler.stop()
        print("Backup scheduler stopped")
    except Exception as e:
        print(f"ERROR: Failed to stop backup scheduler: {e}")


"""
Minimal FastAPI application for initial deployment.
This is a simplified version that includes only core functionality.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create minimal FastAPI app
app = FastAPI(
    title="RoadTrip API - Minimal",
    description="Minimal deployment of RoadTrip backend",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "unknown")
    }


# Detailed health check
@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check for debugging."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "services": {
            "api": "operational",
            "database": "not_configured",
            "redis": "not_configured",
            "ai": "not_configured"
        },
        "env_vars": {
            "GOOGLE_CLOUD_PROJECT": os.getenv("GOOGLE_CLOUD_PROJECT", "not_set"),
            "ENVIRONMENT": os.getenv("ENVIRONMENT", "not_set"),
            "PORT": os.getenv("PORT", "8080")
        }
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to RoadTrip API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


# API v1 health check
@app.get("/api/v1/health")
async def api_health():
    """API v1 health check."""
    return {"status": "ok", "api_version": "v1"}


# Simple auth endpoints (stub for now)
@app.post("/api/auth/login")
async def login(request: Request):
    """Stub login endpoint."""
    body = await request.json()
    # For now, just return a mock response
    return {
        "access_token": "mock_token_for_testing",
        "token_type": "bearer",
        "user": {
            "id": 1,
            "email": body.get("email", "test@example.com"),
            "name": "Test User"
        }
    }


@app.post("/api/auth/register")
async def register(request: Request):
    """Stub register endpoint."""
    body = await request.json()
    return {
        "message": "Registration successful",
        "user": {
            "id": 1,
            "email": body.get("email", "test@example.com"),
            "name": body.get("name", "Test User")
        }
    }


# Simple maps proxy endpoint
@app.get("/api/maps/proxy")
async def maps_proxy(request: Request):
    """Stub maps proxy endpoint."""
    # Extract query parameters
    query_params = dict(request.query_params)
    
    # For now, return a mock response
    return {
        "status": "ok",
        "message": "Maps proxy endpoint (stub)",
        "query": query_params,
        "note": "This will proxy to Google Maps API when configured"
    }


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "path": request.url.path
        }
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting RoadTrip API (Minimal)...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'unknown')}")
    logger.info(f"Project ID: {os.getenv('GOOGLE_CLOUD_PROJECT', 'not set')}")
    logger.info("Startup complete")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down RoadTrip API...")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
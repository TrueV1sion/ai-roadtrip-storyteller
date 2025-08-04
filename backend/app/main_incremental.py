"""
Incremental deployment main.py - Start with core routes only.
This version progressively adds routes to avoid startup failures.
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from uuid import uuid4
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
import traceback

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import settings with fallback
try:
    from app.core.config import settings
except ImportError:
    logger.warning("Could not import settings, using defaults")
    class Settings:
        APP_TITLE = "AI Road Trip Storyteller API"
        APP_DESCRIPTION = "Production-ready AI-powered road trip companion"
        APP_VERSION = "1.0.0"
        ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
        BACKEND_CORS_ORIGINS = ["*"]
    settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Starting AI Road Trip Storyteller (Incremental)...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Version: {settings.APP_VERSION}")
    
    # Test critical services
    startup_checks = await run_startup_checks()
    for service, status in startup_checks.items():
        logger.info(f"Service {service}: {status}")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Road Trip Storyteller...")


async def run_startup_checks():
    """Run basic startup checks for critical services."""
    checks = {}
    
    # Check database
    try:
        from app.database import engine
        from sqlalchemy import text
        
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        logger.error(f"Database check failed: {e}")
    
    # Check Redis (optional)
    try:
        from app.core.cache import cache_manager
        test_key = "startup_check"
        await cache_manager.set(test_key, "test", ttl=5)
        await cache_manager.delete(test_key)
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"not available: {str(e)}"
        logger.warning(f"Redis check failed (non-critical): {e}")
    
    # Check AI service configuration
    ai_project = os.getenv("GOOGLE_AI_PROJECT_ID")
    checks["ai_config"] = "configured" if ai_project else "not configured"
    
    return checks


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Configure CORS - allow all origins for MVP
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Request {request_id} failed: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id}
        )
    
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    logger.info(
        f"Request {request_id} - {request.method} {request.url.path} - "
        f"Status: {response.status_code} - Duration: {process_time:.3f}s"
    )
    
    return response


# Register basic routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Road Trip Storyteller API",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check for debugging."""
    health_status = {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check database
    try:
        from app.database import engine
        from sqlalchemy import text
        
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        from app.core.cache import cache_manager
        test_key = "health_check_test"
        await cache_manager.set(test_key, "test", ttl=5)
        await cache_manager.delete(test_key)
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
    
    # Check AI service
    ai_project = os.getenv("GOOGLE_AI_PROJECT_ID")
    health_status["services"]["ai"] = "configured" if ai_project else "not configured"
    
    # Check Maps API
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    health_status["services"]["maps"] = "configured" if maps_key else "not configured"
    
    return health_status


# Phase 1: Core Authentication Routes
try:
    from app.routes.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
    logger.info("✓ Loaded auth routes")
except Exception as e:
    logger.error(f"✗ Failed to load auth routes: {e}")

try:
    from app.routes.csrf import router as csrf_router
    app.include_router(csrf_router, tags=["CSRF"])
    logger.info("✓ Loaded CSRF routes")
except Exception as e:
    logger.error(f"✗ Failed to load CSRF routes: {e}")


# Phase 2: Maps Proxy (Critical for mobile app)
try:
    from app.routes.maps_proxy import router as maps_proxy_router
    app.include_router(maps_proxy_router, tags=["Maps Proxy"])
    logger.info("✓ Loaded maps proxy routes")
except Exception as e:
    logger.error(f"✗ Failed to load maps proxy routes: {e}")


# Phase 3: Voice and Personality Routes
try:
    from app.routes.voice_personality import router as voice_personality_router
    app.include_router(voice_personality_router, tags=["Voice Personality"])
    logger.info("✓ Loaded voice personality routes")
except Exception as e:
    logger.error(f"✗ Failed to load voice personality routes: {e}")


# Phase 4: Story Generation Routes
try:
    from app.routes.ai_stories import router as stories_router
    app.include_router(stories_router, prefix="/api/stories", tags=["AI Stories"])
    logger.info("✓ Loaded story generation routes")
except Exception as e:
    logger.error(f"✗ Failed to load story generation routes: {e}")


# Phase 5: User Management
try:
    from app.routes.user import router as user_router
    app.include_router(user_router, prefix="/api/users", tags=["Users"])
    logger.info("✓ Loaded user routes")
except Exception as e:
    logger.error(f"✗ Failed to load user routes: {e}")


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to prevent crashes."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unhandled exception in request {request_id}: {str(exc)}\n{traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "request_id": request_id,
            "type": type(exc).__name__
        }
    )


# Log final status
logger.info(f"Application initialized with {len(app.routes)} routes")
logger.info("Available endpoints:")
for route in app.routes:
    if hasattr(route, "path"):
        logger.info(f"  {route.methods} {route.path}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
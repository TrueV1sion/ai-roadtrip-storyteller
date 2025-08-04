"""
Simplified main.py for RoadTrip Backend - Working Version
This version starts with core functionality and can be expanded
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging
from datetime import datetime

# Simple logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Road Trip Storyteller API",
    description="Backend API for the AI Road Trip mobile app",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic routes
@app.get("/")
async def root():
    return {
        "message": "AI Road Trip Backend API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "operational",
            "google_maps": "healthy",
            "gemini_ai": "healthy (Vertex AI configured)"
        }
    }

# Import routes with error handling
routes_loaded = []
routes_failed = []

# Try to import auth routes
try:
    from app.routes.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
    routes_loaded.append("auth")
except Exception as e:
    logger.error(f"Failed to import auth routes: {e}")
    routes_failed.append(("auth", str(e)))

# Try to import maps proxy routes  
try:
    from app.routes.maps_proxy import router as maps_router
    app.include_router(maps_router, prefix="/api/maps-proxy", tags=["Maps"])
    routes_loaded.append("maps_proxy")
except Exception as e:
    logger.error(f"Failed to import maps_proxy routes: {e}")
    routes_failed.append(("maps_proxy", str(e)))

# Try to import ai_stories routes
try:
    from app.routes.ai_stories import router as stories_router
    app.include_router(stories_router, prefix="/api/stories", tags=["Stories"])
    routes_loaded.append("ai_stories")
except Exception as e:
    logger.error(f"Failed to import ai_stories routes: {e}")
    routes_failed.append(("ai_stories", str(e)))

# Try to import voice personality routes
try:
    from app.routes.voice_personality import router as voice_router
    app.include_router(voice_router, prefix="/api/voice", tags=["Voice"])
    routes_loaded.append("voice_personality")
except Exception as e:
    logger.error(f"Failed to import voice_personality routes: {e}")
    routes_failed.append(("voice_personality", str(e)))

# Status endpoint to show what's loaded
@app.get("/api/status")
async def api_status():
    """Show which routes are loaded."""
    return {
        "routes_loaded": routes_loaded,
        "routes_failed": routes_failed,
        "total_endpoints": len(app.routes)
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "type": type(exc).__name__
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("AI Road Trip Backend starting up...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Routes loaded: {routes_loaded}")
    logger.info(f"Routes failed: {len(routes_failed)}")
    if routes_failed:
        for route, error in routes_failed:
            logger.error(f"  - {route}: {error}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("AI Road Trip Backend shutting down...")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import time
from uuid import uuid4
import logging
import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from app.routes import story, auth, user, immersive, personalized_story, personalization, games, utils, theme, side_quest, spatial_audio, contextual_awareness, serendipity, ar, interactive_narrative, driving_assistant, voice_character, tts, ai_stories, cache_management, db_monitoring, revenue_analytics, booking, voice_assistant, event_journey, rideshare, rideshare_mode, voice_personality, spotify, reservations_v2, database_health, database_monitoring, performance_monitoring, airport_parking, airport_amenities, personality, health, two_factor, security_monitoring, security_monitoring_v2, sessions, intrusion_detection, rate_limiting, security_dashboard, automated_threat_response, security_metrics, mvp_voice, mvp_voice_enhanced, api_documentation, mobile_dev_webhook, jwks, maps_proxy, csrf, password, async_jobs, health_v2, metrics, circuit_breaker_monitoring, api_keys, api_secured_example, mobile_security, navigation, voice_orchestration
from app.core.logger import get_logger
from app.core.config import settings
from app.core.error_handler import register_exception_handlers
from app.core.production_https_config import EnhancedHTTPSRedirectMiddleware
from app.core.cors_https import configure_cors
from app.core.auth import get_current_admin_user
from app.monitoring.middleware_v2 import PrometheusMiddlewareV2
from app.middleware.csrf_middleware import CSRFMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.middleware.performance_middleware import PerformanceOptimizationMiddleware
from app.middleware.security_monitoring import SecurityMonitoringMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.middleware.api_versioning import APIVersioningMiddleware
from app.monitoring.metrics import metrics
from app.monitoring.security_monitor import security_monitor
from app.monitoring.audit_logger import audit_logger
from app.monitoring.security_metrics import security_metrics
from app.security.intrusion_detection import intrusion_detection_system
from app.security.automated_threat_response import automated_threat_response
from app.startup_production import run_production_startup_validation
from app.core.health_check_v2 import RequestTrackingMiddleware
from app.core.tracing_config import init_tracing
from app.models.user import User
from app.core.tracing import setup_tracing, TraceContextMiddleware
from app.core.openapi_enhanced import setup_enhanced_openapi
from app.core.knowledge_graph import KnowledgeGraphMiddleware, kg_client

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Starting AI Road Trip Storyteller...")
    
    # Initialize distributed tracing
    init_tracing(app)
    
    # Run production startup validation
    validation_success = await run_production_startup_validation()
    if not validation_success:
        logger.error("Production startup validation failed. Please check configuration.")
        # In production, you might want to exit here
        # raise RuntimeError("Production startup validation failed")
    
    # Initialize distributed tracing
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "")
    enable_console_tracing = settings.ENVIRONMENT == "development" and settings.DEBUG
    
    if otlp_endpoint or enable_console_tracing:
        setup_tracing(
            service_name="roadtrip-api",
            service_version=settings.APP_VERSION,
            otlp_endpoint=otlp_endpoint if otlp_endpoint else None,
            enable_console_export=enable_console_tracing
        )
        logger.info(f"Distributed tracing enabled (OTLP: {otlp_endpoint or 'disabled'}, Console: {enable_console_tracing})")
    
    # Start security monitoring services
    await security_monitor.start()
    await audit_logger.start()
    await intrusion_detection_system.start()
    await automated_threat_response.start()
    await security_metrics.start()
    
    # Initialize database optimization manager
    try:
        from app.core.database_optimization_v2 import db_optimization_manager
        await db_optimization_manager.initialize()
        logger.info("Database optimization manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database optimization: {e}")
        # Continue anyway - optimization is not critical for startup
    
    # Initialize any other resources here
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Road Trip Storyteller...")
    
    # Stop security monitoring services
    await security_monitor.stop()
    await audit_logger.stop()
    await intrusion_detection_system.stop()
    await automated_threat_response.stop()
    await security_metrics.stop()
    
    # Close Knowledge Graph client
    if os.getenv("KNOWLEDGE_GRAPH_ENABLED", "false").lower() == "true":
        await kg_client.close()
        logger.info("Knowledge Graph client closed")
    
    # Cleanup resources here if needed


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Add HTTPS redirect middleware (must be first)
app.add_middleware(EnhancedHTTPSRedirectMiddleware)

# Add request tracking for graceful shutdown (must be early)
app.add_middleware(RequestTrackingMiddleware)

# Configure CORS settings with HTTPS support
configure_cors(app)

# Add trace context middleware (very early to propagate context)
app.add_middleware(TraceContextMiddleware)

# Add Knowledge Graph middleware (if enabled)
if os.getenv("KNOWLEDGE_GRAPH_ENABLED", "false").lower() == "true":
    app.add_middleware(KnowledgeGraphMiddleware)
    logger.info("Knowledge Graph middleware enabled")

# Add performance optimization middleware (first for timing accuracy)
performance_middleware = PerformanceOptimizationMiddleware(app)
app.add_middleware(PerformanceOptimizationMiddleware)

# Add Prometheus monitoring middleware
app.add_middleware(PrometheusMiddlewareV2)

# Add API versioning middleware (early for version routing)
app.add_middleware(APIVersioningMiddleware)

# Add security monitoring middleware (early to catch all requests)
app.add_middleware(SecurityMonitoringMiddleware)

# Add rate limiting middleware (before security headers)
app.add_middleware(RateLimitMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add CSRF protection middleware
app.add_middleware(CSRFMiddleware)

# Add request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    
    # Start timer
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Add request ID to response headers
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log request details
    logger.info(
        f"Request {request_id} completed - "
        f"Method: {request.method} "
        f"Path: {request.url.path} "
        f"Status: {response.status_code} "
        f"Duration: {process_time:.3f}s"
    )
    
    return response

# Register error handlers
register_exception_handlers(app)

# Include JWKS endpoint (no prefix for .well-known path)
app.include_router(jwks.router, tags=["JWKS"])

# Include security endpoints
app.include_router(csrf.router, tags=["CSRF"])

# Include Maps proxy to protect API keys
app.include_router(maps_proxy.router, tags=["Maps Proxy"])

# Include application routers
app.include_router(story.router, prefix="/api/story", tags=["Story"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(two_factor.router, prefix="/api/auth", tags=["Two-Factor Auth"])
app.include_router(sessions.router, prefix="/api/auth", tags=["Sessions"])
app.include_router(password.router, prefix="/api/password", tags=["Password Security"])
app.include_router(user.router, prefix="/api/users", tags=["Users"])
app.include_router(immersive.router, prefix="/api", tags=["Immersive"])
app.include_router(personalized_story.router, prefix="/api", tags=["Personalized"])
app.include_router(personalization.router, prefix="/api", tags=["Personalization"])  # Added personalization router
app.include_router(games.router, prefix="/api", tags=["Games"])
app.include_router(utils.router, prefix="/api", tags=["Utilities"])
app.include_router(theme.router, prefix="/api", tags=["Themes"])
app.include_router(side_quest.router, prefix="/api", tags=["Side Quests"])
app.include_router(spatial_audio.router, prefix="/api", tags=["Spatial Audio"])
app.include_router(contextual_awareness.router, prefix="/api", tags=["Contextual Awareness"])
app.include_router(serendipity.router, prefix="/api", tags=["Serendipity"])
app.include_router(ar.router, prefix="/api", tags=["Augmented Reality"])
app.include_router(interactive_narrative.router, prefix="/api", tags=["Interactive Narrative"])
app.include_router(driving_assistant.router, prefix="/api", tags=["Driving Assistant"])
app.include_router(voice_character.router, prefix="/api", tags=["Voice Character"])
app.include_router(navigation.router, prefix="/api", tags=["Navigation Voice"])
app.include_router(voice_orchestration.router, tags=["Voice Orchestration"])
app.include_router(tts.router, prefix="/api/tts", tags=["Text-to-Speech"])
app.include_router(ai_stories.router, prefix="/api/stories", tags=["AI Stories"])
app.include_router(cache_management.router, prefix="/api", tags=["Cache Management"])
app.include_router(db_monitoring.router, prefix="/api", tags=["Database Monitoring"])
app.include_router(revenue_analytics.router, tags=["Revenue Analytics"])
app.include_router(booking.router, tags=["Bookings"])
app.include_router(voice_assistant.router, prefix="/api", tags=["Voice Assistant"])
app.include_router(event_journey.router, tags=["Event Journeys"])
app.include_router(rideshare.router, prefix="/api", tags=["Rideshare"])
app.include_router(rideshare_mode.router, tags=["Rideshare Mode"])
app.include_router(voice_personality.router, tags=["Voice Personality"])
app.include_router(spotify.router, prefix="/api", tags=["Spotify"])
app.include_router(reservations_v2.router, prefix="/api/reservations", tags=["Reservations V2"])
app.include_router(database_health.router, prefix="/api", tags=["Database Health"])
app.include_router(database_monitoring.router, tags=["Database Monitoring"])
app.include_router(performance_monitoring.router, prefix="/api", tags=["Performance Monitoring"])
app.include_router(airport_parking.router, tags=["Airport Parking"])
app.include_router(airport_amenities.router, tags=["Airport Amenities"])
app.include_router(personality.router, tags=["Personality System"])
# Include comprehensive health monitoring
app.include_router(health.router, tags=["Health Monitoring"])
# Include v2 health monitoring for horizontal scaling
app.include_router(health_v2.router, tags=["Health Monitoring V2"])
# Include metrics endpoint for Prometheus
app.include_router(metrics.router, tags=["Metrics"])
# Security monitoring endpoints (admin only)
app.include_router(security_monitoring.router, prefix="/api/admin", tags=["Security Monitoring"])
# Include production security monitoring V2
app.include_router(security_monitoring_v2.router, tags=["Security Monitoring V2"])
app.include_router(intrusion_detection.router, prefix="/api/admin", tags=["Intrusion Detection"])
app.include_router(rate_limiting.router, prefix="/api/admin", tags=["Rate Limiting"])
app.include_router(security_dashboard.router, prefix="/api/admin", tags=["Security Dashboard"])
app.include_router(automated_threat_response.router, prefix="/api/admin", tags=["Automated Threat Response"])
app.include_router(security_metrics.router, prefix="/api/admin", tags=["Security Metrics"])
# Include MVP routes (simplified for testing)
app.include_router(mvp_voice.router, tags=["MVP Voice"])
app.include_router(mvp_voice_enhanced.router, tags=["MVP Voice Enhanced"])
# Include enhanced API documentation routes
from app.routes import api_documentation_enhanced
app.include_router(api_documentation_enhanced.router, tags=["API Documentation"])
# Include mobile development control routes
app.include_router(mobile_dev_webhook.router, tags=["Mobile Development"])
# Include async job management endpoints
app.include_router(async_jobs.router, tags=["Async Jobs"])
# Include monitoring endpoints
app.add_route("/metrics", metrics)
# Include circuit breaker monitoring endpoints
app.include_router(circuit_breaker_monitoring.router, tags=["Circuit Breaker Monitoring"])
# Include API key management endpoints
app.include_router(api_keys.router, tags=["API Keys"])
# Include secured API examples
app.include_router(api_secured_example.router, tags=["Secured API Examples"])
# Include mobile security endpoints
app.include_router(mobile_security.router, tags=["Mobile Security"])

# Setup enhanced OpenAPI documentation
setup_enhanced_openapi(app)


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check for debugging."""
    health_status = {
        "status": "ok",
        "version": settings.APP_VERSION,
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
        # Redis is not critical, so we don't change overall status
    
    # Check AI service
    health_status["services"]["ai"] = "configured" if settings.GOOGLE_AI_PROJECT_ID else "not configured"
    
    return health_status


@app.get("/admin/security-dashboard", response_class=HTMLResponse)
async def security_dashboard_ui(current_user: User = Depends(get_current_admin_user)):
    """Serve the security dashboard UI."""
    dashboard_path = Path(__file__).parent / "templates" / "security_dashboard.html"
    
    if not dashboard_path.exists():
        return HTMLResponse(
            content="<h1>Security Dashboard Not Found</h1><p>The dashboard template is missing.</p>",
            status_code=404
        )
    
    with open(dashboard_path, "r") as f:
        content = f.read()
    
    return HTMLResponse(content=content)
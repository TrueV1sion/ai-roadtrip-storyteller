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

# Import core dependencies first
from app.core.logger import get_logger
from app.core.config import settings
from app.core.error_handler import register_exception_handlers
from app.core.production_https_config import EnhancedHTTPSRedirectMiddleware
from app.core.cors_https import configure_cors
from app.core.auth import get_current_admin_user
from app.monitoring.middleware_v2 import PrometheusMiddlewareV2
from app.middleware.csrf_middleware import CSRFMiddleware
from app.core.security_headers import EnhancedSecurityHeadersMiddleware, RequestBodySizeLimitMiddleware
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

# Import routes with error handling to prevent startup failures
route_imports = {}
failed_routes = []

# Core routes that must be imported
core_routes = ['health', 'auth', 'csrf', 'jwks', 'maps_proxy']

# All available routes
all_routes = [
    'story', 'auth', 'user', 'immersive', 'personalized_story', 'personalization',
    'games', 'utils', 'theme', 'side_quest', 'spatial_audio', 'contextual_awareness',
    'serendipity', 'ar', 'interactive_narrative', 'driving_assistant', 'voice_character',
    'tts', 'ai_stories', 'cache_management', 'db_monitoring', 'revenue_analytics',
    'booking', 'voice_assistant', 'event_journey', 'rideshare', 'rideshare_mode',
    'voice_personality', 'spotify', 'reservations_v2', 'database_health',
    'database_monitoring', 'performance_monitoring', 'airport_parking',
    'airport_amenities', 'personality', 'health', 'two_factor', 'security_monitoring',
    'security_monitoring_v2', 'sessions', 'intrusion_detection', 'rate_limiting',
    'security_dashboard', 'automated_threat_response', 'security_metrics',
    'mvp_voice', 'mvp_voice_enhanced', 'api_documentation', 'mobile_dev_webhook',
    'jwks', 'maps_proxy', 'csrf', 'password', 'async_jobs', 'health_v2', 'metrics',
    'circuit_breaker_monitoring', 'api_keys', 'api_secured_example',
    'mobile_security', 'navigation', 'voice_orchestration', 'story_timing',
    'journey_tracking', 'service_health', 'security_csp_report', 'csp_example'
]

# Import routes with error handling
for route_name in all_routes:
    try:
        module = __import__(f'app.routes.{route_name}', fromlist=[route_name])
        route_imports[route_name] = getattr(module, 'router', None)
        if route_imports[route_name] is None:
            logger.warning(f"Route module '{route_name}' has no router attribute")
            failed_routes.append((route_name, "No router attribute"))
    except ImportError as e:
        logger.error(f"Failed to import route '{route_name}': {str(e)}")
        failed_routes.append((route_name, str(e)))
        if route_name in core_routes:
            logger.critical(f"Core route '{route_name}' failed to import!")
            # For core routes, we might want to fail fast in production
            # raise
    except Exception as e:
        logger.error(f"Unexpected error importing route '{route_name}': {str(e)}")
        failed_routes.append((route_name, str(e)))

# Log import summary
if failed_routes:
    logger.warning(f"Failed to import {len(failed_routes)} routes: {[r[0] for r in failed_routes]}")
else:
    logger.info(f"Successfully imported all {len(route_imports)} routes")


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
    
    # Initialize story opportunity scheduler
    try:
        from app.services.story_opportunity_scheduler import story_scheduler
        await story_scheduler.start()
        logger.info("Story opportunity scheduler started")
    except Exception as e:
        logger.error(f"Failed to start story scheduler: {e}")
        # Continue anyway - scheduler is not critical for basic operation
    
    # Initialize any other resources here
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Road Trip Storyteller...")
    
    # Stop story scheduler
    try:
        await story_scheduler.stop()
        logger.info("Story opportunity scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping story scheduler: {e}")
    
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

# Add request body size limit middleware (early to reject large requests)
app.add_middleware(RequestBodySizeLimitMiddleware)

# Add rate limiting middleware (before security headers)
app.add_middleware(RateLimitMiddleware)

# Add enhanced security headers middleware with CSP nonce support
app.add_middleware(EnhancedSecurityHeadersMiddleware)

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

# Define route configurations
route_configs = [
    # Core routes (no prefix for .well-known path)
    ('jwks', '', ['JWKS']),
    ('csrf', '', ['CSRF']),
    ('maps_proxy', '', ['Maps Proxy']),
    
    # Authentication routes
    ('auth', '/api/auth', ['Auth']),
    ('two_factor', '/api/auth', ['Two-Factor Auth']),
    ('sessions', '/api/auth', ['Sessions']),
    ('password', '/api/password', ['Password Security']),
    
    # User and profile routes
    ('user', '/api/users', ['Users']),
    ('personality', '', ['Personality System']),
    ('personalization', '/api', ['Personalization']),
    
    # Story and content routes
    ('story', '/api/story', ['Story']),
    ('immersive', '/api', ['Immersive']),
    ('personalized_story', '/api', ['Personalized']),
    ('ai_stories', '/api/stories', ['AI Stories']),
    ('story_timing', '/api/story-timing', ['Story Timing']),
    
    # Voice and audio routes
    ('voice_character', '/api', ['Voice Character']),
    ('voice_personality', '', ['Voice Personality']),
    ('voice_assistant', '/api', ['Voice Assistant']),
    ('voice_orchestration', '', ['Voice Orchestration']),
    ('tts', '/api/tts', ['Text-to-Speech']),
    ('spatial_audio', '/api', ['Spatial Audio']),
    ('navigation', '/api', ['Navigation Voice']),
    
    # Gaming and interactive features
    ('games', '/api', ['Games']),
    ('side_quest', '/api', ['Side Quests']),
    ('interactive_narrative', '/api', ['Interactive Narrative']),
    ('ar', '/api', ['Augmented Reality']),
    
    # Booking and reservations
    ('booking', '', ['Bookings']),
    ('reservations_v2', '/api/reservations', ['Reservations V2']),
    ('airport_parking', '', ['Airport Parking']),
    ('airport_amenities', '', ['Airport Amenities']),
    
    # Journey and location features
    ('event_journey', '', ['Event Journeys']),
    ('journey_tracking', '/api/journey', ['Journey Tracking']),
    ('contextual_awareness', '/api', ['Contextual Awareness']),
    ('serendipity', '/api', ['Serendipity']),
    ('driving_assistant', '/api', ['Driving Assistant']),
    
    # Rideshare features
    ('rideshare', '/api', ['Rideshare']),
    ('rideshare_mode', '', ['Rideshare Mode']),
    
    # External integrations
    ('spotify', '/api', ['Spotify']),
    
    # Utilities and themes
    ('utils', '/api', ['Utilities']),
    ('theme', '/api', ['Themes']),
    
    # Monitoring and health
    ('health', '', ['Health Monitoring']),
    ('health_v2', '', ['Health Monitoring V2']),
    ('service_health', '', ['Service Health']),
    ('metrics', '', ['Metrics']),
    ('performance_monitoring', '/api', ['Performance Monitoring']),
    ('database_health', '/api', ['Database Health']),
    ('database_monitoring', '', ['Database Monitoring']),
    ('db_monitoring', '/api', ['Database Monitoring']),
    ('circuit_breaker_monitoring', '', ['Circuit Breaker Monitoring']),
    
    # Admin and security routes
    ('security_monitoring', '/api/admin', ['Security Monitoring']),
    ('security_monitoring_v2', '', ['Security Monitoring V2']),
    ('intrusion_detection', '/api/admin', ['Intrusion Detection']),
    ('rate_limiting', '/api/admin', ['Rate Limiting']),
    ('security_dashboard', '/api/admin', ['Security Dashboard']),
    ('automated_threat_response', '/api/admin', ['Automated Threat Response']),
    ('security_metrics', '/api/admin', ['Security Metrics']),
    ('security_csp_report', '', ['CSP Reporting']),
    ('api_keys', '', ['API Keys']),
    ('mobile_security', '', ['Mobile Security']),
    
    # Development and documentation
    ('api_documentation', '', ['API Documentation']),
    ('api_secured_example', '', ['Secured API Examples']),
    ('csp_example', '', ['CSP Examples']),
    ('mobile_dev_webhook', '', ['Mobile Development']),
    
    # Other features
    ('cache_management', '/api', ['Cache Management']),
    ('revenue_analytics', '', ['Revenue Analytics']),
    ('async_jobs', '', ['Async Jobs']),
    ('mvp_voice', '', ['MVP Voice']),
    ('mvp_voice_enhanced', '', ['MVP Voice Enhanced']),
]

# Include successfully imported routes
for route_name, prefix, tags in route_configs:
    if route_name in route_imports and route_imports[route_name]:
        try:
            app.include_router(route_imports[route_name], prefix=prefix, tags=tags)
            logger.debug(f"Registered route: {route_name} with prefix: {prefix}")
        except Exception as e:
            logger.error(f"Failed to register route '{route_name}': {str(e)}")
    else:
        logger.warning(f"Skipping route '{route_name}' - not available")

# Special handling for api_documentation_enhanced which is imported differently
try:
    from app.routes import api_documentation_enhanced
    app.include_router(api_documentation_enhanced.router, tags=["API Documentation"])
except Exception as e:
    logger.error(f"Failed to import api_documentation_enhanced: {str(e)}")

# Add metrics route if available
if 'metrics' in route_imports and hasattr(route_imports['metrics'], 'metrics'):
    app.add_route("/metrics", route_imports['metrics'].metrics)

# Log final route count
logger.info(f"Application initialized with {len(app.routes)} routes")

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
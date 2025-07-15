"""
Prometheus Middleware V2 - Production Implementation
Comprehensive request tracking and metrics collection
"""

import time
import asyncio
from typing import Optional, Callable
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.monitoring.metrics_v2 import metrics_v2
from app.core.logger import get_logger

logger = get_logger(__name__)


class PrometheusMiddlewareV2(BaseHTTPMiddleware):
    """Production Prometheus middleware with comprehensive metrics."""
    
    def __init__(self, app: ASGIApp, app_name: str = "roadtrip_api"):
        super().__init__(app)
        self.app_name = app_name
        logger.info("Prometheus Middleware V2 initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect comprehensive metrics."""
        # Extract path template (normalize for metrics)
        path = self._get_path_template(request)
        method = request.method
        
        # Skip metrics endpoint to avoid recursion
        if path == "/metrics":
            return await call_next(request)
        
        # Track active requests
        metrics_v2.track_active_request(method, path, 1)
        
        # Start timing
        start_time = time.time()
        
        # Track request size
        request_size = int(request.headers.get("content-length", 0))
        if request_size > 0:
            metrics_v2.http_request_size_bytes.labels(
                method=method,
                endpoint=path
            ).observe(request_size)
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
        except asyncio.CancelledError:
            # Handle cancelled requests (client disconnect)
            status_code = 499
            logger.warning(f"Request cancelled: {method} {path}")
            raise
            
        except Exception as e:
            # Handle unexpected errors
            status_code = 500
            logger.error(f"Request failed: {method} {path} - {e}")
            response = Response(
                content="Internal Server Error",
                status_code=500,
                headers={
                    "X-Error-Id": str(id(e)),
                    "Cache-Control": "no-cache"
                }
            )
        
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Track request metrics
            metrics_v2.track_request(method, path, status_code)
            
            # Track request duration
            metrics_v2.http_request_duration_seconds.labels(
                method=method,
                endpoint=path
            ).observe(duration)
            
            # Track response size if available
            response_size = int(response.headers.get("content-length", 0))
            if response_size > 0:
                metrics_v2.http_response_size_bytes.labels(
                    method=method,
                    endpoint=path
                ).observe(response_size)
            
            # Track active requests
            metrics_v2.track_active_request(method, path, -1)
            
            # Add custom headers
            response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"
            response.headers["X-Worker-Id"] = str(metrics_v2.worker_info._value._value.get("pid", "unknown"))
            
            # Log request details
            logger.info(
                f"{method} {path} - {status_code} - {duration * 1000:.2f}ms",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration * 1000,
                    "request_size": request_size,
                    "response_size": response_size,
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "request_id": request.headers.get("x-request-id", "unknown")
                }
            )
        
        return response
    
    def _get_path_template(self, request: Request) -> str:
        """Extract path template for metrics (normalize dynamic segments)."""
        path = request.url.path
        
        # Common patterns to normalize
        # Replace UUIDs
        import re
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path
        )
        
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        # Replace common dynamic segments
        replacements = [
            (r'/users/[^/]+', '/users/{user_id}'),
            (r'/stories/[^/]+', '/stories/{story_id}'),
            (r'/trips/[^/]+', '/trips/{trip_id}'),
            (r'/bookings/[^/]+', '/bookings/{booking_id}'),
        ]
        
        for pattern, replacement in replacements:
            path = re.sub(pattern, replacement, path)
        
        return path


class MetricsMiddleware:
    """Additional middleware for business metrics collection."""
    
    def __init__(self, app: ASGIApp):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            
            # Track specific business endpoints
            if "/stories/generate" in path:
                # Will be tracked by story generation service
                pass
            elif "/bookings" in path and scope["method"] == "POST":
                # Will be tracked by booking service
                pass
            elif "/auth/login" in path:
                # Track authentication attempts
                if scope["method"] == "POST":
                    # This will be tracked by auth service
                    pass
        
        await self.app(scope, receive, send)


# Export middleware
__all__ = ['PrometheusMiddlewareV2', 'MetricsMiddleware']
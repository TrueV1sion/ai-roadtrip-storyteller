"""
Performance Optimization Middleware - Stub Implementation
"""

import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class PerformanceOptimizationMiddleware(BaseHTTPMiddleware):
    """Stub implementation of performance optimization middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.slow_request_threshold = 2.0  # seconds
        logger.info("Performance Optimization Middleware initialized (stub)")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Add performance headers (stub)
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        response.headers["X-Performance-Optimized"] = "true"
        
        # Log slow requests
        if duration > self.slow_request_threshold:
            logger.warning(f"Slow request detected: {request.method} {request.url.path} "
                         f"took {duration:.3f}s (stub)")
        
        return response

"""
Prometheus Middleware - Stub Implementation
"""

import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Stub implementation of Prometheus middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.request_duration_total = 0
        logger.info("Prometheus Middleware initialized (stub)")
    
    async def dispatch(self, request: Request, call_next):
        """Process request and collect metrics."""
        start_time = time.time()
        
        # Increment request counter
        self.request_count += 1
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            logger.error(f"Request failed: {e}")
            status_code = 500
            response = Response(content="Internal Server Error", status_code=500)
        
        # Calculate duration
        duration = time.time() - start_time
        self.request_duration_total += duration
        
        # Log metrics (stub)
        logger.debug(f"Request {request.method} {request.url.path} - "
                    f"Status: {status_code}, Duration: {duration:.3f}s (stub)")
        
        return response

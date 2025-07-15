import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp
from prometheus_client import Counter, Histogram

from app.monitoring.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    REQUEST_IN_PROGRESS,
    EXCEPTION_COUNT
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware that collects Prometheus metrics for each request.
    
    Metrics collected:
    - request_count: Total number of requests by path, method, and status code
    - request_latency: Request duration in seconds by path and method
    - request_in_progress: Number of requests currently being processed
    - exception_count: Total number of exceptions raised during request processing
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Increment in-progress counter
        REQUEST_IN_PROGRESS.inc()
        
        # Extract request path and method
        method = request.method
        path = request.url.path
        
        # Skip metrics endpoint
        if path == "/metrics":
            response = await call_next(request)
            return response
        
        # Time the request processing
        start_time = time.time()
        status_code = 500  # Default to error status
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            # Count exceptions
            EXCEPTION_COUNT.labels(
                method=method,
                path=path,
                exception_type=type(exc).__name__
            ).inc()
            raise
        finally:
            # Record request latency
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(
                method=method,
                path=path
            ).observe(duration)
            
            # Count total requests
            REQUEST_COUNT.labels(
                method=method,
                path=path,
                status_code=status_code
            ).inc()
            
            # Decrement in-progress counter
            REQUEST_IN_PROGRESS.dec() 
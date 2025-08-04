"""
Correlation ID middleware for request tracking across services.

This middleware ensures every request has a unique correlation ID that
follows it through all services, logs, and external API calls.
"""

import uuid
import contextvars
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logger import get_logger
from app.core.tracing import add_span_attributes, get_current_trace_id

logger = get_logger(__name__)

# Context variable to store correlation ID
correlation_id_context = contextvars.ContextVar('correlation_id', default=None)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return correlation_id_context.get()


def set_correlation_id(correlation_id: str):
    """Set the correlation ID in context."""
    correlation_id_context.set(correlation_id)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to all requests.
    
    This middleware:
    1. Extracts correlation ID from incoming request headers
    2. Generates a new ID if none exists
    3. Adds the ID to response headers
    4. Makes the ID available throughout request processing
    5. Integrates with OpenTelemetry tracing
    """
    
    def __init__(
        self,
        app,
        header_name: str = "X-Correlation-ID",
        generate_id_func=None
    ):
        super().__init__(app)
        self.header_name = header_name
        self.generate_id_func = generate_id_func or self._generate_correlation_id
    
    def _generate_correlation_id(self) -> str:
        """Generate a new correlation ID."""
        # Use trace ID if available, otherwise generate UUID
        trace_id = get_current_trace_id()
        if trace_id:
            return f"trace-{trace_id}"
        return f"corr-{uuid.uuid4().hex}"
    
    async def dispatch(self, request: Request, call_next):
        # Extract or generate correlation ID
        correlation_id = request.headers.get(self.header_name)
        
        if not correlation_id:
            correlation_id = self.generate_id_func()
            logger.debug(f"Generated new correlation ID: {correlation_id}")
        else:
            logger.debug(f"Using existing correlation ID: {correlation_id}")
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        # Add to request state for easy access
        request.state.correlation_id = correlation_id
        
        # Add to OpenTelemetry span
        add_span_attributes({
            "correlation.id": correlation_id,
            "request.method": request.method,
            "request.url": str(request.url),
            "request.client": request.client.host if request.client else "unknown"
        })
        
        # Log request with correlation ID
        logger.info(
            f"Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id
            
            # Log response
            logger.info(
                f"Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "status_code": response.status_code
                }
            )
            
            return response
            
        except Exception as e:
            # Log error with correlation ID
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise


class CorrelatedHTTPClient:
    """
    HTTP client that automatically includes correlation IDs in outgoing requests.
    """
    
    def __init__(self, client):
        self.client = client
    
    async def request(self, method: str, url: str, **kwargs):
        """Make HTTP request with correlation ID."""
        correlation_id = get_correlation_id()
        
        if correlation_id:
            headers = kwargs.get('headers', {})
            headers['X-Correlation-ID'] = correlation_id
            kwargs['headers'] = headers
            
            logger.debug(
                f"Outgoing HTTP request",
                extra={
                    "correlation_id": correlation_id,
                    "method": method,
                    "url": url
                }
            )
        
        return await self.client.request(method, url, **kwargs)
    
    async def get(self, url: str, **kwargs):
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs):
        return await self.request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs):
        return await self.request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs):
        return await self.request('DELETE', url, **kwargs)


def inject_correlation_id(headers: dict) -> dict:
    """
    Inject correlation ID into headers for outgoing requests.
    
    Use this when making requests to external services.
    """
    correlation_id = get_correlation_id()
    if correlation_id:
        headers['X-Correlation-ID'] = correlation_id
    return headers


def log_with_correlation(
    logger_instance,
    level: str,
    message: str,
    **kwargs
):
    """
    Log a message with correlation ID automatically included.
    """
    correlation_id = get_correlation_id()
    extra = kwargs.get('extra', {})
    extra['correlation_id'] = correlation_id
    kwargs['extra'] = extra
    
    getattr(logger_instance, level)(message, **kwargs)
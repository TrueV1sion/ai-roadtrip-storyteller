"""
HTTPS Redirect Middleware
Ensures all requests use HTTPS in production
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
from typing import Callable
import os


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS.
    Only active in production environments.
    """
    
    def __init__(self, app, force_https: bool = None):
        super().__init__(app)
        # Allow override, otherwise check environment
        if force_https is not None:
            self.force_https = force_https
        else:
            self.force_https = os.getenv("ENVIRONMENT", "development").lower() in ["production", "staging"]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip for local development
        if not self.force_https:
            return await call_next(request)
        
        # Check if request is already HTTPS
        # Handle both direct HTTPS and behind proxy (X-Forwarded-Proto)
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
        
        if request.url.scheme == "https" or forwarded_proto == "https":
            # Already HTTPS, proceed normally
            response = await call_next(request)
            
            # Add HSTS header to response
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
            
            return response
        
        # Redirect to HTTPS
        https_url = request.url.replace(scheme="https")
        
        # Preserve query parameters and path
        return RedirectResponse(
            url=str(https_url),
            status_code=301  # Permanent redirect
        )


def get_https_redirect_middleware(force_https: bool = None):
    """
    Factory function to create HTTPS redirect middleware.
    
    Args:
        force_https: Override environment detection (useful for testing)
    
    Returns:
        HTTPSRedirectMiddleware class configured with settings
    """
    class ConfiguredHTTPSRedirectMiddleware(HTTPSRedirectMiddleware):
        def __init__(self, app):
            super().__init__(app, force_https=force_https)
    
    return ConfiguredHTTPSRedirectMiddleware
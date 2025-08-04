"""
CORS Configuration with HTTPS support
Handles CORS policies for production HTTPS environments
"""

from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import os


def get_cors_origins() -> List[str]:
    """
    Get allowed CORS origins based on environment.
    
    Returns:
        List of allowed origin URLs
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "development":
        # Allow specific development origins only - no wildcards
        origins = [
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://localhost:8000",
            "http://localhost:8080",
            "http://localhost:19006",  # Expo web
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:19006",
        ]
        
        # Add specific local network IPs if needed (no wildcards)
        local_ips = os.getenv("LOCAL_DEV_IPS", "").split(",")
        for ip in local_ips:
            ip = ip.strip()
            if ip:
                origins.extend([
                    f"http://{ip}:3000",
                    f"http://{ip}:8000",
                    f"http://{ip}:19006"
                ])
        
        return origins
    
    elif env in ["staging", "production"]:
        # Production origins (HTTPS only)
        base_origins = [
            "https://app.roadtrip.ai",
            "https://www.roadtrip.ai",
            "https://api.roadtrip.ai",
            "https://admin.roadtrip.ai",
        ]
        
        if env == "staging":
            # Add staging domains
            base_origins.extend([
                "https://staging.roadtrip.ai",
                "https://api-staging.roadtrip.ai",
            ])
        
        # Add any additional origins from environment
        additional_origins = os.getenv("CORS_ORIGINS", "").split(",")
        for origin in additional_origins:
            origin = origin.strip()
            if origin and origin.startswith("https://"):
                base_origins.append(origin)
        
        return base_origins
    
    # No wildcard fallback - fail safe by returning empty list
    return []


def configure_cors(app, 
                  allow_origins: Optional[List[str]] = None,
                  allow_credentials: bool = True,
                  allow_methods: List[str] = None,
                  allow_headers: List[str] = None,
                  expose_headers: Optional[List[str]] = None) -> None:
    """
    Configure CORS middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
        allow_origins: Override default origins
        allow_credentials: Allow credentials in CORS requests
        allow_methods: Allowed HTTP methods
        allow_headers: Allowed headers
        expose_headers: Headers to expose to the browser
    """
    # Use provided origins or get from environment
    origins = allow_origins or get_cors_origins()
    
    # Specific allowed methods - no wildcards
    if allow_methods is None:
        allow_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
    
    # Specific allowed headers - no wildcards
    if allow_headers is None:
        allow_headers = [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-CSRF-Token",
            "X-Request-ID",
            "X-API-Key",
            "Cache-Control",
            "Pragma"
        ]
    
    # Default exposed headers
    if expose_headers is None:
        expose_headers = [
            "X-Total-Count",
            "X-Page-Count", 
            "X-Current-Page",
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Process-Time",
            "X-API-Version"
        ]
    
    # Add CORS middleware with strict configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
        expose_headers=expose_headers,
        max_age=3600,  # 1 hour (reduced from 24 hours for security)
    )


def validate_origin(origin: str, allowed_origins: Optional[List[str]] = None) -> bool:
    """
    Validate if an origin is allowed for CORS.
    
    Args:
        origin: Origin to validate
        allowed_origins: List of allowed origins (uses defaults if None)
        
    Returns:
        True if origin is allowed
    """
    if not origin:
        return False
    
    allowed = allowed_origins or get_cors_origins()
    
    # Only allow exact matches - no wildcards for security
    return origin in allowed


def get_origin_from_request(request) -> Optional[str]:
    """
    Extract origin from request headers.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Origin string or None
    """
    return request.headers.get("Origin") or request.headers.get("Referer")
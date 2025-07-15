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
        # Allow common development origins
        return [
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://localhost:8080",
            "http://localhost:19006",  # Expo web
            "http://192.168.*.*:*",    # Local network for mobile dev
            "http://10.0.*.*:*",       # Local network variations
            "exp://localhost:*",        # Expo development
        ]
    
    elif env in ["staging", "production"]:
        # Production origins (HTTPS only)
        base_origins = [
            "https://roadtrip.app",
            "https://www.roadtrip.app",
            "https://api.roadtrip.app",
            "https://admin.roadtrip.app",
        ]
        
        if env == "staging":
            # Add staging domains
            base_origins.extend([
                "https://staging.roadtrip.app",
                "https://api-staging.roadtrip.app",
            ])
        
        # Add any additional origins from environment
        additional_origins = os.getenv("CORS_ORIGINS", "").split(",")
        for origin in additional_origins:
            origin = origin.strip()
            if origin and origin.startswith("https://"):
                base_origins.append(origin)
        
        return base_origins
    
    return ["*"]  # Fallback (not recommended)


def configure_cors(app, 
                  allow_origins: Optional[List[str]] = None,
                  allow_credentials: bool = True,
                  allow_methods: List[str] = ["*"],
                  allow_headers: List[str] = ["*"],
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
        ]
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
        expose_headers=expose_headers,
        max_age=86400,  # 24 hours
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
    
    # Check exact matches
    if origin in allowed:
        return True
    
    # Check wildcard patterns
    for allowed_origin in allowed:
        if "*" in allowed_origin:
            # Simple wildcard matching (e.g., "http://192.168.*.*:*")
            pattern = allowed_origin.replace(".", r"\.").replace("*", ".*")
            import re
            if re.match(f"^{pattern}$", origin):
                return True
    
    return False


def get_origin_from_request(request) -> Optional[str]:
    """
    Extract origin from request headers.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Origin string or None
    """
    return request.headers.get("Origin") or request.headers.get("Referer")
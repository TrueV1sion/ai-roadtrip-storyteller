"""
Security Headers Middleware
Adds comprehensive security headers to all responses
"""

from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import time
from ..core.config import get_settings

settings = get_settings()


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to all responses
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Process the request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Request-ID"] = request.state.request_id if hasattr(request.state, "request_id") else "unknown"
        response.headers["X-Process-Time"] = str(process_time)
        
        # HSTS header (only in production)
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self' https://apis.google.com https://www.googleapis.com",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://apis.google.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self' https://api.roadtripstoryteller.com wss://api.roadtripstoryteller.com https://maps.googleapis.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "upgrade-insecure-requests"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Permissions Policy
        permissions_policy = [
            "geolocation=(self)",
            "microphone=(self)",
            "camera=()",
            "payment=()",
            "usb=()",
            "accelerometer=()",
            "gyroscope=()",
            "magnetometer=()",
            "interest-cohort=()"
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)
        
        # Remove server header
        response.headers.pop("server", None)
        
        # Add custom headers for API versioning
        response.headers["X-API-Version"] = "1.0.0"
        
        # CORS headers (if not already set by FastAPI CORS middleware)
        if "access-control-allow-origin" not in response.headers:
            # These would typically be set by FastAPI's CORS middleware
            # Only adding as fallback
            if settings.CORS_ORIGINS:
                origin = request.headers.get("origin")
                if origin in settings.CORS_ORIGINS:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response


def get_security_headers() -> dict:
    """
    Get dictionary of security headers for static configuration
    """
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    
    if not settings.DEBUG:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    return headers


class SecurityEventLogger:
    """
    Logger for security-related events
    """
    
    @staticmethod
    async def log_security_event(
        event_type: str,
        request: Request,
        details: dict = None,
        severity: str = "INFO"
    ):
        """
        Log a security event
        """
        from ..core.logging import logger
        
        event_data = {
            "event_type": event_type,
            "severity": severity,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "path": request.url.path,
            "method": request.method,
            "timestamp": time.time()
        }
        
        if hasattr(request.state, "user"):
            event_data["user_id"] = request.state.user.id
        
        if details:
            event_data.update(details)
        
        # Log to application logger
        logger.info(f"Security Event: {event_type}", extra=event_data)
        
        # In production, this would also send to SIEM
        if not settings.DEBUG:
            # Send to Cloud Logging with security label
            pass


# Security utility functions
def sanitize_user_input(input_string: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks
    """
    if not input_string:
        return ""
    
    # Truncate to max length
    input_string = input_string[:max_length]
    
    # Remove null bytes
    input_string = input_string.replace('\x00', '')
    
    # Basic HTML entity encoding
    replacements = {
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;'
    }
    
    for char, replacement in replacements.items():
        input_string = input_string.replace(char, replacement)
    
    return input_string


def validate_file_upload(filename: str, content_type: str, max_size: int) -> tuple[bool, str]:
    """
    Validate file uploads for security
    """
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/gif': ['.gif'],
        'audio/mpeg': ['.mp3'],
        'audio/wav': ['.wav'],
        'application/pdf': ['.pdf']
    }
    
    # Check content type
    if content_type not in ALLOWED_EXTENSIONS:
        return False, "Invalid file type"
    
    # Check file extension
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if f".{file_ext}" not in ALLOWED_EXTENSIONS[content_type]:
        return False, "File extension does not match content type"
    
    # Check for double extensions
    if filename.count('.') > 1:
        return False, "Multiple file extensions not allowed"
    
    # Check for path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        return False, "Invalid filename"
    
    return True, "Valid"
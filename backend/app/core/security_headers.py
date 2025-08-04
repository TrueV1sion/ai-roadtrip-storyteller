"""
Enhanced Security Headers Middleware with CSP Nonce Support
Implements OWASP security best practices with strict CSP
"""

import secrets
import hashlib
import base64
from typing import Callable, Dict, Optional, Set
from fastapi import Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
import time
import logging
from ..core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Constants for security configuration
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB default
MAX_UPLOAD_SIZE = 50 * 1024 * 1024   # 50MB for file uploads
NONCE_LENGTH = 32  # 256 bits of entropy


class EnhancedSecurityHeadersMiddleware:
    """
    Enhanced middleware with CSP nonce support and comprehensive security headers
    """
    
    def __init__(self, app):
        self.app = app
        # Production allowed origins - no wildcards
        self.allowed_origins = self._get_allowed_origins()
        # Endpoint-specific body size limits
        self.body_size_limits = {
            "/api/v1/upload": MAX_UPLOAD_SIZE,
            "/api/v1/photos": MAX_UPLOAD_SIZE,
            "/api/v1/audio": MAX_UPLOAD_SIZE,
            # Add more endpoints as needed
        }
    
    def _get_allowed_origins(self) -> Set[str]:
        """Get allowed origins based on environment"""
        if settings.ENVIRONMENT == "production":
            return {
                "https://app.roadtrip.ai",
                "https://www.roadtrip.ai",
                "https://api.roadtrip.ai"
            }
        elif settings.ENVIRONMENT == "staging":
            return {
                "https://staging.roadtrip.ai",
                "https://api-staging.roadtrip.ai"
            }
        else:  # development
            return {
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000"
            }
    
    def _generate_nonce(self) -> str:
        """Generate cryptographically secure nonce for CSP"""
        return base64.b64encode(secrets.token_bytes(NONCE_LENGTH)).decode('utf-8')
    
    def _get_content_type(self, response: Response) -> str:
        """Extract content type from response headers"""
        content_type = response.headers.get("content-type", "")
        return content_type.split(";")[0].strip().lower()
    
    def _build_csp_header(self, nonce: str, is_api_endpoint: bool) -> str:
        """Build Content Security Policy header with nonce support"""
        if is_api_endpoint:
            # Strict CSP for API endpoints (no HTML/scripts expected)
            return "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        
        # CSP for web content with nonce-based script execution
        csp_directives = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}' https://apis.google.com https://www.googleapis.com",
            "style-src 'self' 'nonce-{nonce}' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https: blob:",
            f"connect-src 'self' {' '.join(self.allowed_origins)} https://maps.googleapis.com wss://api.roadtrip.ai",
            "media-src 'self' blob:",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "upgrade-insecure-requests",
            "block-all-mixed-content",
            "require-trusted-types-for 'script'"
        ]
        
        # Add report-uri in production for CSP violation monitoring
        if settings.ENVIRONMENT == "production":
            csp_directives.append("report-uri /api/v1/security/csp-report")
        
        return "; ".join(csp_directives)
    
    def _build_permissions_policy(self) -> str:
        """Build Permissions Policy header"""
        permissions = {
            "accelerometer": "()",
            "ambient-light-sensor": "()",
            "autoplay": "(self)",
            "battery": "()",
            "camera": "()",
            "display-capture": "()",
            "document-domain": "()",
            "encrypted-media": "(self)",
            "execution-while-not-rendered": "()",
            "execution-while-out-of-viewport": "()",
            "fullscreen": "(self)",
            "gamepad": "()",
            "geolocation": "(self)",
            "gyroscope": "()",
            "interest-cohort": "()",  # Disable FLoC
            "magnetometer": "()",
            "microphone": "(self)",  # For voice features
            "midi": "()",
            "navigation-override": "()",
            "payment": "()",
            "picture-in-picture": "()",
            "publickey-credentials-get": "()",
            "screen-wake-lock": "()",
            "sync-xhr": "()",
            "usb": "()",
            "web-share": "(self)",
            "xr-spatial-tracking": "()"
        }
        
        return ", ".join([f"{key}={value}" for key, value in permissions.items()])
    
    def _get_body_size_limit(self, path: str) -> int:
        """Get request body size limit for specific endpoint"""
        for endpoint, limit in self.body_size_limits.items():
            if path.startswith(endpoint):
                return limit
        return MAX_REQUEST_SIZE
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Check request body size before processing
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length:
                size_limit = self._get_body_size_limit(request.url.path)
                if int(content_length) > size_limit:
                    logger.warning(
                        f"Request body too large: {content_length} bytes for {request.url.path}"
                    )
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request entity too large"}
                    )
        
        # Generate nonce for this request
        nonce = self._generate_nonce()
        
        # Store nonce in request state for use in templates/responses
        request.state.csp_nonce = nonce
        
        # Check origin for CORS
        origin = request.headers.get("origin")
        if origin and origin not in self.allowed_origins:
            logger.warning(f"Rejected request from unauthorized origin: {origin}")
            if settings.ENVIRONMENT == "production":
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Origin not allowed"}
                )
        
        # Process the request
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Determine if this is an API endpoint
        is_api_endpoint = request.url.path.startswith("/api/") or \
                         request.url.path.startswith("/v1/") or \
                         request.url.path.startswith("/v2/")
        
        # Add comprehensive security headers
        security_headers = {
            # Core security headers
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "0",  # Disabled in modern browsers, CSP is better
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "X-Request-ID": request.state.request_id if hasattr(request.state, "request_id") else str(secrets.token_urlsafe(16)),
            "X-Process-Time": str(process_time),
            
            # CSP with nonce
            "Content-Security-Policy": self._build_csp_header(nonce, is_api_endpoint),
            
            # Permissions Policy
            "Permissions-Policy": self._build_permissions_policy(),
            
            # Additional security headers
            "X-Permitted-Cross-Domain-Policies": "none",
            "X-Download-Options": "noopen",
            "X-DNS-Prefetch-Control": "off",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
            
            # Cache control for security
            "Cache-Control": "no-store, no-cache, must-revalidate, private" if is_api_endpoint else "public, max-age=3600",
            "Pragma": "no-cache" if is_api_endpoint else None,
            "Expires": "0" if is_api_endpoint else None,
            
            # API versioning
            "X-API-Version": settings.APP_VERSION,
        }
        
        # HSTS header (only in production and staging)
        if settings.ENVIRONMENT in ["production", "staging"]:
            security_headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        
        # Apply headers
        for header, value in security_headers.items():
            if value is not None:
                response.headers[header] = value
        
        # Remove sensitive headers
        sensitive_headers = ["Server", "X-Powered-By", "X-AspNet-Version", "X-AspNetMvc-Version"]
        for header in sensitive_headers:
            response.headers.pop(header.lower(), None)
        
        # Add CORS headers if origin is allowed
        if origin and origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-CSRF-Token, X-Request-ID"
            response.headers["Access-Control-Expose-Headers"] = "X-Total-Count, X-Page, X-Per-Page, X-Request-ID"
            response.headers["Access-Control-Max-Age"] = "3600"
        
        # Set Vary header for proper caching with CORS
        vary_headers = response.headers.get("Vary", "").split(", ")
        if "Origin" not in vary_headers:
            vary_headers.append("Origin")
        response.headers["Vary"] = ", ".join(filter(None, vary_headers))
        
        # Log security events for monitoring
        if process_time > 5.0:  # Log slow requests
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} took {process_time:.2f}s",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "process_time": process_time,
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "ip": request.client.host if request.client else "unknown"
                }
            )
        
        return response


class RequestBodySizeLimitMiddleware:
    """
    Middleware to enforce request body size limits with streaming support
    """
    
    def __init__(self, app, default_limit: int = MAX_REQUEST_SIZE):
        self.app = app
        self.default_limit = default_limit
        self.endpoint_limits = {
            "/api/v1/upload": MAX_UPLOAD_SIZE,
            "/api/v1/photos": MAX_UPLOAD_SIZE,
            "/api/v1/audio": MAX_UPLOAD_SIZE,
            "/api/v1/stories/generate": 1024 * 1024,  # 1MB for story generation
            # Add more specific limits as needed
        }
    
    def get_limit_for_path(self, path: str) -> int:
        """Get size limit for specific path"""
        for endpoint, limit in self.endpoint_limits.items():
            if path.startswith(endpoint):
                return limit
        return self.default_limit
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        if request.method in ["POST", "PUT", "PATCH"]:
            # Get size limit for this endpoint
            size_limit = self.get_limit_for_path(request.url.path)
            
            # Check Content-Length header
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > size_limit:
                logger.warning(
                    f"Request body too large: {content_length} bytes for {request.url.path}"
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Request entity too large. Maximum size: {size_limit} bytes"
                    }
                )
            
            # For streaming requests without Content-Length, we need to monitor the body
            # This is handled by the framework's built-in limits
        
        return await call_next(request)


class CSPReportingEndpoint:
    """
    Endpoint to receive CSP violation reports
    """
    
    @staticmethod
    async def handle_csp_report(request: Request):
        """Handle CSP violation reports"""
        try:
            report = await request.json()
            logger.warning(
                "CSP Violation Report",
                extra={
                    "report": report,
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "ip": request.client.host if request.client else "unknown"
                }
            )
            # In production, send to security monitoring service
            if settings.ENVIRONMENT == "production":
                # Send to SIEM or monitoring service
                pass
        except Exception as e:
            logger.error(f"Failed to process CSP report: {e}")
        
        return Response(status_code=204)


def get_nonce_from_request(request: Request) -> Optional[str]:
    """
    Get CSP nonce from request state
    Use this in templates to add nonce to inline scripts
    """
    return getattr(request.state, "csp_nonce", None)


def create_nonce_script_tag(script_content: str, nonce: str) -> str:
    """
    Create a script tag with CSP nonce
    Use this helper when generating HTML with inline scripts
    """
    return f'<script nonce="{nonce}">{script_content}</script>'


def create_nonce_style_tag(style_content: str, nonce: str) -> str:
    """
    Create a style tag with CSP nonce
    Use this helper when generating HTML with inline styles
    """
    return f'<style nonce="{nonce}">{style_content}</style>'


# Security utility functions
def sanitize_user_input(input_string: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks
    """
    if not input_string:
        return ""
    
    # Truncate to max length
    input_string = input_string[:max_length]
    
    # Remove null bytes and other control characters
    input_string = ''.join(char for char in input_string if ord(char) >= 32 or char in '\n\r\t')
    
    # HTML entity encoding for common XSS vectors
    replacements = {
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
        '&': '&amp;',
        '=': '&#x3D;',
        '`': '&#x60;',
        '!': '&#x21;',
        '@': '&#x40;',
        '$': '&#x24;',
        '%': '&#x25;',
        '(': '&#x28;',
        ')': '&#x29;',
        '+': '&#x2B;',
        '{': '&#x7B;',
        '}': '&#x7D;',
        '[': '&#x5B;',
        ']': '&#x5D;'
    }
    
    for char, replacement in replacements.items():
        input_string = input_string.replace(char, replacement)
    
    return input_string


def validate_file_upload(filename: str, content_type: str, file_size: int) -> tuple[bool, str]:
    """
    Validate file uploads for security with enhanced checks
    """
    # Allowed MIME types and extensions
    ALLOWED_TYPES = {
        'image/jpeg': {'.jpg', '.jpeg'},
        'image/png': {'.png'},
        'image/gif': {'.gif'},
        'image/webp': {'.webp'},
        'audio/mpeg': {'.mp3'},
        'audio/wav': {'.wav'},
        'audio/ogg': {'.ogg'},
        'application/pdf': {'.pdf'}
    }
    
    # Maximum file sizes by type
    MAX_SIZES = {
        'image': 10 * 1024 * 1024,  # 10MB for images
        'audio': 50 * 1024 * 1024,  # 50MB for audio
        'application': 20 * 1024 * 1024  # 20MB for PDFs
    }
    
    # Check content type
    if content_type not in ALLOWED_TYPES:
        return False, f"File type '{content_type}' not allowed"
    
    # Extract and validate extension
    if '.' not in filename:
        return False, "File must have an extension"
    
    # Check for path traversal attempts
    if any(char in filename for char in ['..', '/', '\\', '\x00']):
        return False, "Invalid characters in filename"
    
    # Get file extension
    file_ext = '.' + filename.rsplit('.', 1)[1].lower()
    
    # Check if extension matches content type
    if file_ext not in ALLOWED_TYPES[content_type]:
        return False, f"File extension '{file_ext}' does not match content type '{content_type}'"
    
    # Check for double extensions or suspicious patterns
    name_parts = filename.lower().split('.')
    if len(name_parts) > 2:
        # Check for dangerous double extensions
        suspicious_extensions = {'.php', '.exe', '.sh', '.bat', '.cmd', '.com', '.scr', '.vbs', '.js'}
        for ext in name_parts[:-1]:
            if '.' + ext in suspicious_extensions:
                return False, "Suspicious double extension detected"
    
    # Check file size
    type_category = content_type.split('/')[0]
    max_size = MAX_SIZES.get(type_category, MAX_SIZES['application'])
    if file_size > max_size:
        return False, f"File too large. Maximum size: {max_size} bytes"
    
    # Additional security checks
    # Check for null bytes
    if '\x00' in filename:
        return False, "Null bytes not allowed in filename"
    
    # Check filename length
    if len(filename) > 255:
        return False, "Filename too long"
    
    # Check for Unicode tricks
    try:
        filename.encode('ascii')
    except UnicodeEncodeError:
        # Allow Unicode but check for homograph attacks
        if any(ord(char) in range(0x200B, 0x200F) for char in filename):
            return False, "Hidden characters detected in filename"
    
    return True, "Valid"


def generate_security_headers_for_static_files() -> Dict[str, str]:
    """
    Generate security headers for static file responses
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "0",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Cache-Control": "public, max-age=31536000, immutable",  # 1 year for static assets
        "X-Permitted-Cross-Domain-Policies": "none",
        "Cross-Origin-Resource-Policy": "same-origin"
    }


class SecurityEventLogger:
    """
    Enhanced logger for security-related events
    """
    
    @staticmethod
    async def log_security_event(
        event_type: str,
        request: Request,
        details: Optional[Dict] = None,
        severity: str = "INFO"
    ):
        """
        Log a security event with additional context
        """
        event_data = {
            "event_type": event_type,
            "severity": severity,
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "path": request.url.path,
            "method": request.method,
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", "unknown")
        }
        
        # Add user info if available
        if hasattr(request.state, "user") and request.state.user:
            event_data["user_id"] = request.state.user.id
            event_data["username"] = request.state.user.username
        
        # Add additional details
        if details:
            event_data.update(details)
        
        # Log based on severity
        if severity == "CRITICAL":
            logger.critical(f"Security Event: {event_type}", extra=event_data)
        elif severity == "ERROR":
            logger.error(f"Security Event: {event_type}", extra=event_data)
        elif severity == "WARNING":
            logger.warning(f"Security Event: {event_type}", extra=event_data)
        else:
            logger.info(f"Security Event: {event_type}", extra=event_data)
        
        # In production, send to SIEM
        if settings.ENVIRONMENT == "production":
            # Forward to security monitoring service
            # This would integrate with your SIEM solution
            pass
"""
Security Headers Middleware
"""

from fastapi import Request
from fastapi.responses import Response
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Add security headers to all responses"""
    
    def __init__(self, app):
        self.app = app
        self.security_headers = {
            # Prevent XSS attacks
            "X-XSS-Protection": "1; mode=block",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable HSTS
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.roadtrip.ai wss://api.roadtrip.ai; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy
            "Permissions-Policy": (
                "geolocation=(self), "
                "microphone=(self), "
                "camera=(), "
                "payment=(), "
                "usb=()"
            ),
            
            # Additional headers
            "X-Permitted-Cross-Domain-Policies": "none",
            "X-Download-Options": "noopen",
            "X-DNS-Prefetch-Control": "off"
        }
    
    async def __call__(self, request: Request, call_next):
        # Process request
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        # Remove sensitive headers
        sensitive_headers = ["Server", "X-Powered-By"]
        for header in sensitive_headers:
            if header in response.headers:
                del response.headers[header]
        
        return response


# CORS configuration with security
from fastapi.middleware.cors import CORSMiddleware


def configure_cors(app):
    """Configure CORS with security in mind"""
    
    # Allowed origins (update for production)
    origins = [
        "https://app.roadtrip.ai",
        "https://www.roadtrip.ai",
        "http://localhost:3000",  # Development only
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count", "X-Page", "X-Per-Page"],
        max_age=86400,  # 24 hours
    )


# CSRF Protection
import secrets
from typing import Optional


class CSRFProtection:
    """CSRF protection using double submit cookies"""
    
    def __init__(self):
        self.token_name = "csrf_token"
        self.header_name = "X-CSRF-Token"
    
    def generate_token(self) -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)
    
    def validate_token(self, cookie_token: Optional[str], header_token: Optional[str]) -> bool:
        """Validate CSRF token"""
        if not cookie_token or not header_token:
            return False
        
        return secrets.compare_digest(cookie_token, header_token)
    
    async def __call__(self, request: Request, call_next):
        # Skip CSRF for safe methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return await call_next(request)
        
        # Get tokens
        cookie_token = request.cookies.get(self.token_name)
        header_token = request.headers.get(self.header_name)
        
        # Validate
        if not self.validate_token(cookie_token, header_token):
            return Response(
                content="CSRF validation failed",
                status_code=403
            )
        
        # Process request
        response = await call_next(request)
        
        # Set new token if needed
        if not cookie_token:
            new_token = self.generate_token()
            response.set_cookie(
                key=self.token_name,
                value=new_token,
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=86400
            )
        
        return response


# Initialize middleware
csrf_protection = CSRFProtection()

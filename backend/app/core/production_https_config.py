"""
Production HTTPS and security configuration.
Enforces HTTPS and implements security best practices.
"""

from typing import Dict, Any, Optional
import os

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class ProductionSecurityConfig:
    """Production security configuration with HTTPS enforcement."""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers for production."""
        headers = {
            # HTTPS enforcement
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # XSS Protection
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy (formerly Feature Policy)
            "Permissions-Policy": (
                "camera=(), "
                "microphone=(self), "  # Allow for voice features
                "geolocation=(self), "  # Allow for location features
                "payment=(self)"  # Allow for payment processing
            ),
            
            # Cache Control for security
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            
            # Additional security
            "X-Permitted-Cross-Domain-Policies": "none",
        }
        
        # Content Security Policy
        if settings.CSP_ENABLED:
            csp_directives = {
                "default-src": ["'self'"],
                "script-src": ["'self'"] + settings.CSP_SCRIPT_SRC,
                "style-src": ["'self'"] + settings.CSP_STYLE_SRC,
                "img-src": ["'self'"] + settings.CSP_IMG_SRC,
                "font-src": ["'self'"] + settings.CSP_FONT_SRC,
                "connect-src": ["'self'"] + settings.CSP_CONNECT_SRC,
                "media-src": ["'self'"] + settings.CSP_MEDIA_SRC,
                "object-src": ["'none'"],
                "frame-ancestors": ["'none'"],
                "base-uri": ["'self'"],
                "form-action": ["'self'"],
                "upgrade-insecure-requests": [],
                "block-all-mixed-content": []
            }
            
            # Build CSP string
            csp_parts = []
            for directive, sources in csp_directives.items():
                if sources:
                    csp_parts.append(f"{directive} {' '.join(sources)}")
                else:
                    csp_parts.append(directive)
            
            headers["Content-Security-Policy"] = "; ".join(csp_parts)
        
        return headers
    
    @staticmethod
    def get_cookie_settings() -> Dict[str, Any]:
        """Get secure cookie settings for production."""
        return {
            "secure": True,  # HTTPS only
            "httponly": True,  # No JavaScript access
            "samesite": "strict",  # CSRF protection
            "max_age": 3600 * 24 * 7,  # 7 days
            "path": "/",
            "domain": None  # Use default domain
        }
    
    @staticmethod
    def validate_production_settings():
        """Validate that production security settings are properly configured."""
        errors = []
        
        # Check HTTPS enforcement
        if not settings.FORCE_HTTPS:
            errors.append("FORCE_HTTPS must be True in production")
        
        # Check secure cookies
        if not settings.SECURE_COOKIES:
            errors.append("SECURE_COOKIES must be True in production")
        
        # Check environment
        if settings.ENVIRONMENT != "production":
            logger.warning("Running security validation in non-production environment")
        
        # Check secret keys
        if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY == "dev-secret-key-change-in-production":
            errors.append("JWT_SECRET_KEY must be set to a secure value")
        
        # Check CORS origins
        if "*" in settings.ALLOWED_ORIGINS:
            errors.append("CORS should not allow all origins in production")
        
        # Check debug mode
        if settings.DEBUG:
            errors.append("DEBUG must be False in production")
        
        if errors:
            error_msg = "Production security validation failed:\n" + "\n".join(f"- {e}" for e in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("Production security settings validated successfully")
        return True
    
    @staticmethod
    def get_cors_config() -> Dict[str, Any]:
        """Get CORS configuration for production."""
        return {
            "allow_origins": settings.ALLOWED_ORIGINS,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-CSRF-Token",
                "X-Request-ID"
            ],
            "expose_headers": [
                "X-Request-ID",
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset"
            ],
            "max_age": 3600  # 1 hour
        }


# Enhanced HTTPS redirect middleware for production
class EnhancedHTTPSRedirectMiddleware:
    """Enhanced HTTPS redirect with security headers."""
    
    def __init__(self, app):
        self.app = app
        self.security_config = ProductionSecurityConfig()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            
            # Check if already HTTPS
            proto = headers.get(b"x-forwarded-proto", b"").decode()
            if proto == "https" or scope["scheme"] == "https":
                # Add security headers to HTTPS responses
                async def send_with_headers(message):
                    if message["type"] == "http.response.start":
                        # Add security headers
                        security_headers = self.security_config.get_security_headers()
                        
                        for name, value in security_headers.items():
                            message["headers"].append(
                                (name.encode(), value.encode())
                            )
                    
                    await send(message)
                
                await self.app(scope, receive, send_with_headers)
            else:
                # Redirect to HTTPS
                host = headers.get(b"host", b"localhost").decode()
                path = scope.get("path", "/")
                query = scope.get("query_string", b"").decode()
                
                https_url = f"https://{host}{path}"
                if query:
                    https_url += f"?{query}"
                
                await send({
                    "type": "http.response.start",
                    "status": 301,
                    "headers": [
                        (b"location", https_url.encode()),
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": b"Redirecting to HTTPS",
                })
        else:
            await self.app(scope, receive, send)


# Production environment validator
def validate_production_environment():
    """Validate production environment configuration."""
    try:
        ProductionSecurityConfig.validate_production_settings()
        
        # Additional checks
        if not os.getenv("GOOGLE_CLOUD_PROJECT"):
            raise ValueError("GOOGLE_CLOUD_PROJECT must be set in production")
        
        if not os.getenv("DATABASE_URL"):
            raise ValueError("DATABASE_URL must be set in production")
        
        # Check for development values
        dev_indicators = [
            ("localhost" in os.getenv("DATABASE_URL", ""), "DATABASE_URL contains localhost"),
            (os.getenv("ENVIRONMENT") == "development", "ENVIRONMENT is set to development"),
            (os.getenv("DEBUG", "").lower() == "true", "DEBUG is enabled")
        ]
        
        for condition, message in dev_indicators:
            if condition:
                logger.warning(f"Production warning: {message}")
        
        logger.info("Production environment validation completed")
        return True
        
    except Exception as e:
        logger.error(f"Production environment validation failed: {e}")
        raise


# Cookie security helper
def create_secure_cookie(
    name: str,
    value: str,
    max_age: Optional[int] = None
) -> Dict[str, Any]:
    """Create a secure cookie configuration."""
    config = ProductionSecurityConfig.get_cookie_settings()
    
    if max_age:
        config["max_age"] = max_age
    
    # In production, ensure secure flag
    if settings.ENVIRONMENT == "production" and not config.get("secure"):
        raise ValueError("Cookies must be secure in production")
    
    return {
        "key": name,
        "value": value,
        **config
    }
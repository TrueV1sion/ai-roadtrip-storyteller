from fastapi import Request, HTTPException, status, Response, Depends
from fastapi.security import APIKeyCookie
from typing import Optional, Dict, Any
from jose import jwt, JWTError
import os
import secrets
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# CSRF Settings
CSRF_SECRET = settings.SECRET_KEY  # Reuse JWT secret for simplicity
CSRF_TOKEN_BYTES = 32  # 256 bits
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_COOKIE_SECURE = True  # Set to False in development if not using HTTPS
CSRF_COOKIE_HTTP_ONLY = True
CSRF_COOKIE_SAMESITE = "lax"  # "strict" for higher security, "lax" for better UX
CSRF_COOKIE_PATH = "/"
# Set to True to only protect authenticated routes
CSRF_EXEMPT_UNAUTHENTICATED = False  

# Cookie security
csrf_cookie = APIKeyCookie(name=CSRF_COOKIE_NAME, auto_error=False)


def generate_csrf_token() -> str:
    """Generate a secure random token for CSRF protection."""
    return secrets.token_hex(CSRF_TOKEN_BYTES)


def generate_signed_token() -> str:
    """Generate a signed CSRF token with timestamp."""
    token = generate_csrf_token()
    payload = {
        "token": token,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    
    return jwt.encode(payload, CSRF_SECRET, algorithm="HS256")


def verify_csrf_token(signed_token: str, request_token: str) -> bool:
    """Verify that the request token matches the cookie token."""
    try:
        payload = jwt.decode(signed_token, CSRF_SECRET, algorithms=["HS256"])
        stored_token = payload.get("token")
        
        if not stored_token:
            return False
            
        # Constant time comparison to prevent timing attacks
        return secrets.compare_digest(stored_token, request_token)
    except JWTError:
        return False


def get_csrf_token_from_cookie(request: Request) -> Optional[str]:
    """Extract CSRF token from cookie."""
    return request.cookies.get(CSRF_COOKIE_NAME)


def get_csrf_token_from_header(request: Request) -> Optional[str]:
    """Extract CSRF token from header."""
    return request.headers.get(CSRF_HEADER_NAME)


def set_csrf_cookie(response: Response) -> None:
    """Set CSRF token cookie in the response."""
    signed_token = generate_signed_token()
    
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=signed_token,
        httponly=CSRF_COOKIE_HTTP_ONLY,
        secure=CSRF_COOKIE_SECURE,
        samesite=CSRF_COOKIE_SAMESITE,
        path=CSRF_COOKIE_PATH,
        max_age=86400  # 24 hours
    )


def get_csrf_protection_enabled(request: Request) -> bool:
    """Determine if CSRF protection should be applied to this request."""
    # Skip CSRF validation for safe methods
    if request.method in CSRF_SAFE_METHODS:
        return False
        
    # Skip for specific API endpoints if needed
    path = request.url.path
    if path.startswith("/api/auth/login") or path.startswith("/api/auth/register"):
        # First login/register doesn't have CSRF token yet
        return False
        
    # Skip for unauthenticated requests if configured that way
    if CSRF_EXEMPT_UNAUTHENTICATED:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return False
            
    return True


async def csrf_protect(
    request: Request,
    csrf_cookie_token: str = Depends(csrf_cookie)
) -> None:
    """
    Middleware dependency to enforce CSRF protection.
    
    Usage:
        @router.post("/endpoint", dependencies=[Depends(csrf_protect)])
        async def endpoint(): ...
    """
    if not get_csrf_protection_enabled(request):
        return
        
    cookie_token = csrf_cookie_token
    header_token = get_csrf_token_from_header(request)
    
    if not cookie_token or not header_token:
        logger.warning(f"CSRF attack detected: Missing token from {'cookie' if not cookie_token else 'header'}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid"
        )
        
    if not verify_csrf_token(cookie_token, header_token):
        logger.warning("CSRF attack detected: Token validation failed")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token invalid"
        )
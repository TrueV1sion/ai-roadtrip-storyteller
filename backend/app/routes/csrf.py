"""
CSRF token endpoint for frontend applications.
Provides a way to fetch CSRF tokens for API requests.
"""
from fastapi import APIRouter, Request, Response
from typing import Dict

router = APIRouter(prefix="/api/csrf", tags=["CSRF"])


@router.get("/token", response_model=Dict[str, str])
async def get_csrf_token(request: Request, response: Response):
    """
    Get a CSRF token for use in API requests.
    
    This endpoint will set a CSRF cookie and return the token value
    that should be included in subsequent POST/PUT/DELETE requests.
    
    The token should be sent in the X-CSRF-Token header.
    
    Returns:
        Dict containing the CSRF token
    """
    # The CSRF middleware will automatically set the cookie and header
    # when it sees a GET request without an existing token
    
    # Get the token from the response header (set by middleware)
    token = response.headers.get("X-CSRF-Token")
    
    # If no token in header, check cookie
    if not token:
        token = request.cookies.get("csrf_token")
    
    # If still no token, generate one manually
    if not token:
        from app.middleware.csrf_middleware import CSRFMiddleware
        csrf_middleware = CSRFMiddleware(None)
        token = csrf_middleware._generate_csrf_token()
        
        # Set cookie
        response.set_cookie(
            key="csrf_token",
            value=token,
            max_age=14400,  # 4 hours
            httponly=False,
            secure=request.url.scheme == "https",
            samesite="strict",
            path="/"
        )
        
        # Set header
        response.headers["X-CSRF-Token"] = token
    
    return {
        "csrf_token": token,
        "header_name": "X-CSRF-Token"
    }
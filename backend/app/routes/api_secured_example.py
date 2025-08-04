"""
Example secured API endpoints demonstrating API key authentication
Shows how to use API keys and request signing
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from app.core.api_security import (
    api_security,
    APIKeyModel,
    APIVersion,
    verify_api_request,
    require_api_key,
    require_permission
)
from app.core.logger import get_logger
from app.schemas.story import StoryRequest, StoryResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v2/secured", tags=["Secured API Examples"])


@router.get("/public")
async def public_endpoint() -> Dict[str, Any]:
    """
    Public endpoint - no API key required.
    
    This endpoint is accessible without authentication.
    """
    return {
        "message": "This is a public endpoint",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "v2"
    }


@router.get("/authenticated")
async def authenticated_endpoint(
    api_key_data: APIKeyModel = Depends(require_api_key)
) -> Dict[str, Any]:
    """
    Authenticated endpoint - requires valid API key.
    
    Pass your API key in the X-API-Key header.
    """
    return {
        "message": "Successfully authenticated",
        "client": api_key_data.client_name,
        "permissions": api_key_data.permissions,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/signed")
async def signed_endpoint(
    request_data: Dict[str, Any],
    api_data: Tuple[Optional[APIKeyModel], APIVersion] = Depends(verify_api_request)
) -> Dict[str, Any]:
    """
    Signed endpoint - requires API key and valid signature.
    
    This endpoint requires:
    - X-API-Key: Your API key
    - X-Signature: HMAC signature of the request
    - X-Timestamp: Unix timestamp
    - X-Nonce: Unique nonce
    - X-API-Version: API version (optional)
    """
    key_data, version = api_data
    
    if not key_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    
    return {
        "message": "Request signature verified",
        "client": key_data.client_name,
        "version": version.value,
        "data_received": request_data,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/stories/generate")
async def generate_story_secured(
    story_request: StoryRequest,
    api_key_data: APIKeyModel = Depends(require_permission("stories"))
) -> StoryResponse:
    """
    Generate story with API key authentication.
    
    Requires 'stories' permission in API key.
    """
    # Check rate limit
    if api_key_data.usage_count >= api_key_data.rate_limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )
    
    # In production, this would call the actual story generation service
    return StoryResponse(
        story_id=f"story_{datetime.utcnow().timestamp()}",
        content=f"A wonderful story generated for {api_key_data.client_name}...",
        title="API Key Authenticated Story",
        location={
            "latitude": story_request.location.latitude,
            "longitude": story_request.location.longitude,
            "name": "Generated Location"
        },
        metadata={
            "api_version": "v2",
            "client": api_key_data.client_name,
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@router.get("/version-example")
async def version_example(
    api_data: Tuple[Optional[APIKeyModel], APIVersion] = Depends(verify_api_request)
) -> Dict[str, Any]:
    """
    Example showing API versioning.
    
    The response format changes based on the API version header.
    """
    key_data, version = api_data
    
    if version == APIVersion.V1:
        # V1 response format (legacy)
        return {
            "data": "Version 1 response format",
            "created": datetime.utcnow().timestamp(),  # V1 uses timestamps
            "api_key": key_data.key_id if key_data else None
        }
    else:
        # V2 response format (current)
        return {
            "data": {
                "message": "Version 2 response format",
                "features": ["Enhanced security", "Better performance", "More features"]
            },
            "created_at": datetime.utcnow().isoformat(),  # V2 uses ISO format
            "metadata": {
                "api_key": key_data.key_id if key_data else None,
                "version": version.value
            }
        }


@router.get("/permissions-example")
async def permissions_example() -> Dict[str, Any]:
    """
    Example showing available permissions.
    
    Different endpoints require different permissions.
    """
    return {
        "available_permissions": [
            {
                "permission": "read",
                "description": "Basic read access to public data"
            },
            {
                "permission": "write", 
                "description": "Create and update resources"
            },
            {
                "permission": "delete",
                "description": "Delete resources"
            },
            {
                "permission": "stories",
                "description": "Generate AI stories"
            },
            {
                "permission": "bookings",
                "description": "Create and manage bookings"
            },
            {
                "permission": "voice",
                "description": "Access voice synthesis features"
            },
            {
                "permission": "analytics",
                "description": "Access analytics data"
            },
            {
                "permission": "users",
                "description": "Manage user accounts"
            },
            {
                "permission": "*",
                "description": "Full admin access"
            }
        ],
        "example_endpoints": {
            "/api/v2/secured/authenticated": ["Any valid API key"],
            "/api/v2/secured/signed": ["Any valid API key with signature"],
            "/api/v2/stories/generate": ["stories permission"],
            "/api/v2/bookings": ["bookings permission"],
            "/api/v2/voice/tts": ["voice permission"],
            "/api/v2/analytics": ["analytics permission"],
            "/api/v2/admin/*": ["admin permission or * permission"]
        }
    }
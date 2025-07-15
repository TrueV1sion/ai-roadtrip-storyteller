"""
API Key Schemas
Request/Response models for API key management
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class APIKeyPermission(str, Enum):
    """Available API permissions."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    STORIES = "stories"
    BOOKINGS = "bookings"
    VOICE = "voice"
    ANALYTICS = "analytics"
    USERS = "users"
    ALL = "*"


class APIKeyCreate(BaseModel):
    """Request model for creating an API key."""
    client_name: str = Field(..., min_length=3, max_length=100, description="Name of the client/application")
    permissions: List[str] = Field(..., description="List of permissions to grant")
    description: Optional[str] = Field(None, max_length=500, description="Description of key usage")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Key expiration in days")
    rate_limit: Optional[int] = Field(1000, ge=10, le=10000, description="Requests per hour")
    
    @validator('permissions')
    def validate_permissions(cls, v):
        """Validate permissions are valid."""
        valid_permissions = [p.value for p in APIKeyPermission]
        for perm in v:
            if perm not in valid_permissions:
                raise ValueError(f"Invalid permission: {perm}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "client_name": "Mobile App Production",
                "permissions": ["stories", "bookings", "voice"],
                "description": "Production API key for mobile application",
                "expires_in_days": 365,
                "rate_limit": 5000
            }
        }


class APIKeyResponse(BaseModel):
    """Response model for API key details."""
    key_id: str = Field(..., description="Unique key identifier")
    secret_key: Optional[str] = Field(None, description="Secret key (only shown on creation)")
    client_name: str = Field(..., description="Client/application name")
    permissions: List[str] = Field(..., description="Granted permissions")
    rate_limit: int = Field(..., description="Requests per hour limit")
    is_active: bool = Field(..., description="Whether key is active")
    created_at: str = Field(..., description="Creation timestamp")
    expires_at: Optional[str] = Field(None, description="Expiration timestamp")
    last_used_at: Optional[str] = Field(None, description="Last usage timestamp")
    usage_count: int = Field(0, description="Total usage count")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    warning: Optional[str] = Field(None, description="Important warnings")
    
    class Config:
        schema_extra = {
            "example": {
                "key_id": "ak_1234567890abcdef",
                "secret_key": "sk_abcdef1234567890abcdef1234567890",
                "client_name": "Mobile App Production",
                "permissions": ["stories", "bookings", "voice"],
                "rate_limit": 5000,
                "is_active": True,
                "created_at": "2025-07-11T10:00:00Z",
                "expires_at": "2026-07-11T10:00:00Z",
                "last_used_at": None,
                "usage_count": 0,
                "warning": "Save the secret_key securely. It will not be shown again."
            }
        }


class APIKeyListItem(BaseModel):
    """API key item in list response."""
    key_id: str
    client_name: str
    permissions: List[str]
    rate_limit: int
    is_active: bool
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    usage_count: int


class APIKeyListResponse(BaseModel):
    """Response model for listing API keys."""
    total: int = Field(..., description="Total number of keys")
    keys: List[APIKeyListItem] = Field(..., description="List of API keys")
    
    class Config:
        schema_extra = {
            "example": {
                "total": 2,
                "keys": [
                    {
                        "key_id": "ak_1234567890abcdef",
                        "client_name": "Mobile App Production",
                        "permissions": ["stories", "bookings", "voice"],
                        "rate_limit": 5000,
                        "is_active": True,
                        "created_at": "2025-07-11T10:00:00Z",
                        "expires_at": "2026-07-11T10:00:00Z",
                        "last_used_at": "2025-07-11T14:30:00Z",
                        "usage_count": 1234
                    }
                ]
            }
        }


class APIKeyUsageResponse(BaseModel):
    """Response model for API key usage statistics."""
    key_id: str = Field(..., description="API key identifier")
    client_name: str = Field(..., description="Client name")
    time_range: str = Field(..., description="Time range for statistics")
    total_requests: int = Field(..., description="Total requests in period")
    last_used_at: Optional[str] = Field(None, description="Last usage timestamp")
    rate_limit: int = Field(..., description="Current rate limit")
    rate_limit_remaining: int = Field(..., description="Remaining requests in current window")
    usage_by_endpoint: Dict[str, int] = Field(..., description="Request count by endpoint")
    usage_by_hour: List[Dict[str, Any]] = Field(..., description="Hourly usage data")
    
    class Config:
        schema_extra = {
            "example": {
                "key_id": "ak_1234567890abcdef",
                "client_name": "Mobile App Production",
                "time_range": "24h",
                "total_requests": 860,
                "last_used_at": "2025-07-11T14:30:00Z",
                "rate_limit": 5000,
                "rate_limit_remaining": 4140,
                "usage_by_endpoint": {
                    "/api/v2/stories/generate": 450,
                    "/api/v2/bookings": 230,
                    "/api/v2/voice/tts": 180
                },
                "usage_by_hour": [
                    {"hour": "2025-07-11T14:00:00", "requests": 45},
                    {"hour": "2025-07-11T13:00:00", "requests": 52}
                ]
            }
        }


class APIKeyValidationResponse(BaseModel):
    """Response model for API key validation."""
    valid: bool = Field(..., description="Whether key is valid")
    message: Optional[str] = Field(None, description="Validation message")
    client_name: Optional[str] = Field(None, description="Client name if valid")
    permissions: Optional[List[str]] = Field(None, description="Permissions if valid")
    rate_limit: Optional[int] = Field(None, description="Rate limit if valid")
    expires_at: Optional[str] = Field(None, description="Expiration if valid")
    
    class Config:
        schema_extra = {
            "example": {
                "valid": True,
                "client_name": "Mobile App Production",
                "permissions": ["stories", "bookings", "voice"],
                "rate_limit": 5000,
                "expires_at": "2026-07-11T10:00:00Z"
            }
        }


class SignatureExampleRequest(BaseModel):
    """Request for signature example generation."""
    method: str = Field("POST", description="HTTP method")
    path: str = Field("/api/v2/stories/generate", description="API endpoint path")
    api_key: str = Field(..., description="Your API key")
    secret_key: str = Field(..., description="Your secret key")
    
    class Config:
        schema_extra = {
            "example": {
                "method": "POST",
                "path": "/api/v2/stories/generate",
                "api_key": "ak_1234567890abcdef",
                "secret_key": "sk_abcdef1234567890abcdef1234567890"
            }
        }


class SignatureExampleResponse(BaseModel):
    """Response with signature example and code samples."""
    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="Full URL")
    headers: Dict[str, str] = Field(..., description="Required headers")
    body: Optional[Dict[str, Any]] = Field(None, description="Request body")
    code_examples: Dict[str, str] = Field(..., description="Code examples in different languages")
    
    class Config:
        schema_extra = {
            "example": {
                "method": "POST",
                "url": "https://api.roadtrip.ai/api/v2/stories/generate",
                "headers": {
                    "X-API-Key": "ak_1234567890abcdef",
                    "X-Signature": "a1b2c3d4e5f6...",
                    "X-Timestamp": "1720706400",
                    "X-Nonce": "unique_nonce_123",
                    "X-API-Version": "v2",
                    "Content-Type": "application/json"
                },
                "body": {
                    "location": {
                        "latitude": 34.0522,
                        "longitude": -118.2437
                    },
                    "interests": ["history", "architecture"]
                },
                "code_examples": {
                    "python": "# Python code example...",
                    "javascript": "// JavaScript code example...",
                    "curl": "# cURL command example..."
                }
            }
        }
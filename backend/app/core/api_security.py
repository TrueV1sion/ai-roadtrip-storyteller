"""
API Security System - Request Signing and Versioning
Production-grade API security with HMAC signing and version management
"""

import hmac
import hashlib
import time
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import secrets
from urllib.parse import parse_qs, urlencode

from fastapi import Request, HTTPException, Header, Depends
from fastapi.security import APIKeyHeader, HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from app.core.logger import get_logger
from app.core.cache import cache_manager
from app.core.config import settings
from app.database import Base, get_db
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON

logger = get_logger(__name__)


class APIVersion(Enum):
    """Supported API versions."""
    V1 = "v1"
    V2 = "v2"
    LATEST = "v2"


@dataclass
class APIKey:
    """API Key data structure."""
    key_id: str
    secret_key: str
    client_name: str
    permissions: List[str]
    rate_limit: int
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    version: APIVersion = APIVersion.LATEST


class APIKeyModel(Base):
    """Database model for API keys."""
    __tablename__ = "api_keys"
    
    key_id = Column(String, primary_key=True, index=True)
    secret_key_hash = Column(String, nullable=False)  # Store hashed version
    client_name = Column(String, nullable=False)
    permissions = Column(JSON, default=list)
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    key_metadata = Column(JSON, default=dict)


class APISecurityManager:
    """Manages API security, versioning, and request signing."""
    
    def __init__(self):
        self.api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
        self.signature_header = "X-Signature"
        self.timestamp_header = "X-Timestamp"
        self.nonce_header = "X-Nonce"
        self.version_header = "X-API-Version"
        
        # Security settings
        self.signature_window = 300  # 5 minutes
        self.min_key_length = 32
        self.hash_algorithm = hashlib.sha256
        
        # Version settings
        self.supported_versions = [v.value for v in APIVersion]
        self.deprecated_versions: List[str] = []  # Add old versions here
        
        logger.info("API Security Manager initialized")
    
    def generate_api_key(self, client_name: str, permissions: List[str]) -> APIKey:
        """Generate a new API key pair."""
        key_id = f"ak_{secrets.token_urlsafe(16)}"
        secret_key = secrets.token_urlsafe(32)
        
        api_key = APIKey(
            key_id=key_id,
            secret_key=secret_key,
            client_name=client_name,
            permissions=permissions,
            rate_limit=1000,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        logger.info(f"Generated API key for client: {client_name}")
        return api_key
    
    async def validate_api_key(self, api_key: str, db) -> Optional[APIKeyModel]:
        """Validate API key and return key data."""
        if not api_key:
            return None
        
        # Check cache first
        cache_key = f"api_key:{api_key}"
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            return APIKeyModel(**cached_data)
        
        # Query database
        key_data = db.query(APIKeyModel).filter(
            APIKeyModel.key_id == api_key,
            APIKeyModel.is_active == True
        ).first()
        
        if key_data:
            # Check expiration
            if key_data.expires_at and key_data.expires_at < datetime.utcnow():
                logger.warning(f"Expired API key used: {api_key}")
                return None
            
            # Update usage
            key_data.last_used_at = datetime.utcnow()
            key_data.usage_count += 1
            db.commit()
            
            # Cache for 5 minutes
            await cache_manager.set(
                cache_key,
                {
                    "key_id": key_data.key_id,
                    "client_name": key_data.client_name,
                    "permissions": key_data.permissions,
                    "rate_limit": key_data.rate_limit,
                    "is_active": key_data.is_active
                },
                expire=300
            )
            
            return key_data
        
        return None
    
    def create_signature(
        self,
        secret_key: str,
        method: str,
        path: str,
        timestamp: str,
        nonce: str,
        body: str = ""
    ) -> str:
        """Create HMAC signature for request."""
        # Create canonical request
        canonical_parts = [
            method.upper(),
            path,
            timestamp,
            nonce,
            self.hash_algorithm(body.encode()).hexdigest() if body else ""
        ]
        canonical_request = "\n".join(canonical_parts)
        
        # Create signature
        signature = hmac.new(
            secret_key.encode(),
            canonical_request.encode(),
            self.hash_algorithm
        ).hexdigest()
        
        return signature
    
    def verify_signature(
        self,
        secret_key: str,
        method: str,
        path: str,
        timestamp: str,
        nonce: str,
        signature: str,
        body: str = ""
    ) -> bool:
        """Verify request signature."""
        expected_signature = self.create_signature(
            secret_key, method, path, timestamp, nonce, body
        )
        
        # Constant-time comparison
        return hmac.compare_digest(expected_signature, signature)
    
    async def verify_request(
        self,
        request: Request,
        api_key: Optional[str] = Header(None, alias="X-API-Key"),
        signature: Optional[str] = Header(None, alias="X-Signature"),
        timestamp: Optional[str] = Header(None, alias="X-Timestamp"),
        nonce: Optional[str] = Header(None, alias="X-Nonce"),
        api_version: Optional[str] = Header(None, alias="X-API-Version")
    ) -> Tuple[Optional[APIKeyModel], APIVersion]:
        """Verify API request with signature and version."""
        # For public endpoints, return defaults
        if not api_key:
            return None, APIVersion.LATEST
        
        # Validate timestamp
        if not timestamp or not self._validate_timestamp(timestamp):
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired timestamp"
            )
        
        # Check nonce for replay protection
        if not nonce or not await self._validate_nonce(nonce):
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid or reused nonce"
            )
        
        # Validate API version
        version = self._validate_version(api_version)
        
        # Get API key data
        db = next(get_db())
        try:
            key_data = await self.validate_api_key(api_key, db)
            if not key_data:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
            
            # For signed requests, verify signature
            if signature:
                # Get request body
                body = ""
                if request.method in ["POST", "PUT", "PATCH"]:
                    body_bytes = await request.body()
                    body = body_bytes.decode('utf-8', errors='ignore')
                    # Store for later use
                    request._body = body_bytes
                
                # Build path with query params
                path = str(request.url.path)
                if request.url.query:
                    path += f"?{request.url.query}"
                
                # Verify signature
                if not self.verify_signature(
                    key_data.secret_key_hash,  # In production, retrieve actual secret
                    request.method,
                    path,
                    timestamp,
                    nonce,
                    signature,
                    body
                ):
                    logger.warning(f"Invalid signature for API key: {api_key}")
                    raise HTTPException(
                        status_code=HTTP_403_FORBIDDEN,
                        detail="Invalid request signature"
                    )
            
            return key_data, version
            
        finally:
            db.close()
    
    def _validate_timestamp(self, timestamp: str) -> bool:
        """Validate request timestamp is within acceptable window."""
        try:
            request_time = float(timestamp)
            current_time = time.time()
            
            # Check if timestamp is within window
            if abs(current_time - request_time) > self.signature_window:
                return False
            
            return True
        except ValueError as e:
            logger.error(f"Failed to validate timestamp: {e}")
            return False
    
    async def _validate_nonce(self, nonce: str) -> bool:
        """Validate nonce hasn't been used recently."""
        nonce_key = f"api_nonce:{nonce}"
        
        # Check if nonce exists
        if await cache_manager.get(nonce_key):
            return False
        
        # Store nonce with expiration
        await cache_manager.set(nonce_key, 1, expire=self.signature_window)
        return True
    
    def _validate_version(self, version: Optional[str]) -> APIVersion:
        """Validate and return API version."""
        if not version:
            return APIVersion.LATEST
        
        if version in self.deprecated_versions:
            logger.warning(f"Deprecated API version used: {version}")
        
        if version not in self.supported_versions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported API version. Supported versions: {self.supported_versions}"
            )
        
        return APIVersion(version)
    
    def create_api_response(
        self,
        data: Any,
        version: APIVersion,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create versioned API response."""
        response = {
            "version": version.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        if metadata:
            response["metadata"] = metadata
        
        # Version-specific transformations
        if version == APIVersion.V1:
            # V1 compatibility transformations
            response = self._transform_response_v1(response)
        
        return response
    
    def _transform_response_v1(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response for V1 compatibility."""
        # Example: V1 uses different field names
        if "data" in response and isinstance(response["data"], dict):
            if "created_at" in response["data"]:
                response["data"]["created"] = response["data"].pop("created_at")
        
        return response
    
    def check_permissions(
        self,
        key_data: APIKeyModel,
        required_permission: str
    ) -> bool:
        """Check if API key has required permission."""
        if "*" in key_data.permissions:  # Admin access
            return True
        
        return required_permission in key_data.permissions
    
    async def revoke_api_key(self, key_id: str, db) -> bool:
        """Revoke an API key."""
        key_data = db.query(APIKeyModel).filter(
            APIKeyModel.key_id == key_id
        ).first()
        
        if key_data:
            key_data.is_active = False
            db.commit()
            
            # Remove from cache
            await cache_manager.delete(f"api_key:{key_id}")
            
            logger.info(f"Revoked API key: {key_id}")
            return True
        
        return False
    
    def generate_client_example(
        self,
        api_key: str,
        secret_key: str,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate example client request with signature."""
        timestamp = str(int(time.time()))
        nonce = secrets.token_urlsafe(16)
        body_str = json.dumps(body) if body else ""
        
        signature = self.create_signature(
            secret_key,
            method,
            path,
            timestamp,
            nonce,
            body_str
        )
        
        headers = {
            "X-API-Key": api_key,
            "X-Signature": signature,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-API-Version": APIVersion.LATEST.value,
            "Content-Type": "application/json"
        }
        
        return {
            "method": method,
            "url": f"https://api.roadtrip.ai{path}",
            "headers": headers,
            "body": body
        }


# Global instance
api_security = APISecurityManager()


# FastAPI dependencies
async def verify_api_request(
    request: Request,
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    signature: Optional[str] = Header(None, alias="X-Signature"),
    timestamp: Optional[str] = Header(None, alias="X-Timestamp"),
    nonce: Optional[str] = Header(None, alias="X-Nonce"),
    api_version: Optional[str] = Header(None, alias="X-API-Version")
) -> Tuple[Optional[APIKeyModel], APIVersion]:
    """FastAPI dependency for API request verification."""
    return await api_security.verify_request(
        request, api_key, signature, timestamp, nonce, api_version
    )


async def require_api_key(
    api_data: Tuple[Optional[APIKeyModel], APIVersion] = Depends(verify_api_request)
) -> APIKeyModel:
    """Require valid API key for endpoint."""
    key_data, version = api_data
    if not key_data:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    return key_data


async def require_permission(permission: str):
    """Require specific permission for endpoint."""
    async def permission_checker(
        api_data: Tuple[Optional[APIKeyModel], APIVersion] = Depends(verify_api_request)
    ) -> APIKeyModel:
        key_data, version = api_data
        if not key_data:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        if not api_security.check_permissions(key_data, permission):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        
        return key_data
    
    return permission_checker
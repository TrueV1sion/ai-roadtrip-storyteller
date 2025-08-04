"""
API Versioning Middleware
Handles API version routing and compatibility
"""

import re
from typing import Dict, Any, Optional, Callable, List
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logger import get_logger
from app.core.api_security import APIVersion
from app.core.config import settings

logger = get_logger(__name__)


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """Middleware for API versioning support."""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Version routing patterns
        self.version_patterns = {
            # URL path versioning: /api/v1/resource
            "path": re.compile(r"^/api/(v\d+)/(.*)$"),
            # Accept header versioning: application/vnd.api+json;version=1
            "accept": re.compile(r"version=(\d+)"),
        }
        
        # Version transformers
        self.request_transformers: Dict[str, Callable] = {}
        self.response_transformers: Dict[str, Callable] = {}
        
        # Deprecated endpoints
        self.deprecated_endpoints = {
            "v1": {
                "/api/v1/story/generate": "Use /api/v2/stories/generate instead",
                "/api/v1/auth/token": "Use /api/v2/auth/login instead"
            }
        }
        
        # Version-specific features
        self.version_features = {
            "v1": {
                "rate_limit": 100,
                "response_format": "legacy",
                "error_format": "simple"
            },
            "v2": {
                "rate_limit": 1000,
                "response_format": "standard",
                "error_format": "detailed"
            }
        }
        
        logger.info("API Versioning Middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with version handling."""
        # Extract version from request
        version = self._extract_version(request)
        
        # Store version in request state
        request.state.api_version = version
        
        # Check for deprecated endpoints
        deprecation_warning = self._check_deprecation(request, version)
        
        # Transform request if needed
        request = await self._transform_request(request, version)
        
        # Add version to metrics/logging context
        logger.info(f"API request: {request.method} {request.url.path} (version: {version})")
        
        # Process request
        response = await call_next(request)
        
        # Transform response based on version
        response = await self._transform_response(response, version)
        
        # Add version headers
        response.headers["X-API-Version"] = version
        response.headers["X-Supported-Versions"] = "v1, v2"
        
        # Add deprecation warning if applicable
        if deprecation_warning:
            response.headers["X-Deprecation-Warning"] = deprecation_warning
            response.headers["Sunset"] = "2025-12-31"  # Deprecation date
        
        return response
    
    def _extract_version(self, request: Request) -> str:
        """Extract API version from request."""
        # 1. Check URL path versioning
        path_match = self.version_patterns["path"].match(str(request.url.path))
        if path_match:
            return path_match.group(1)
        
        # 2. Check header versioning
        version_header = request.headers.get("x-api-version")
        if version_header and version_header in ["v1", "v2"]:
            return version_header
        
        # 3. Check Accept header versioning
        accept_header = request.headers.get("accept", "")
        accept_match = self.version_patterns["accept"].search(accept_header)
        if accept_match:
            return f"v{accept_match.group(1)}"
        
        # 4. Check query parameter (least preferred)
        version_param = request.query_params.get("api_version")
        if version_param and version_param in ["v1", "v2"]:
            return version_param
        
        # Default to latest version
        return APIVersion.LATEST.value
    
    def _check_deprecation(self, request: Request, version: str) -> Optional[str]:
        """Check if endpoint is deprecated."""
        path = str(request.url.path)
        
        if version in self.deprecated_endpoints:
            for deprecated_path, message in self.deprecated_endpoints[version].items():
                if path.startswith(deprecated_path):
                    return message
        
        return None
    
    async def _transform_request(self, request: Request, version: str) -> Request:
        """Transform request based on version."""
        # V1 to V2 transformations
        if version == "v1":
            # Example: V1 uses different parameter names
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    # Get body
                    body = await request.body()
                    if body:
                        import json
                        data = json.loads(body)
                        
                        # Transform field names
                        if "user_name" in data:
                            data["username"] = data.pop("user_name")
                        if "pass_word" in data:
                            data["password"] = data.pop("pass_word")
                        
                        # Store transformed body
                        request._body = json.dumps(data).encode()
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse request body for version transformation: {e}")
                    pass
        
        return request
    
    async def _transform_response(self, response: Response, version: str) -> Response:
        """Transform response based on version."""
        # Only transform JSON responses
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                # Read response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                if body:
                    import json
                    data = json.loads(body)
                    
                    # Apply version-specific transformations
                    if version == "v1":
                        data = self._transform_response_v1(data)
                    elif version == "v2":
                        data = self._transform_response_v2(data)
                    
                    # Create new response with transformed data
                    return JSONResponse(
                        content=data,
                        status_code=response.status_code,
                        headers=dict(response.headers)
                    )
            except Exception as e:
                logger.error(f"Error transforming response: {e}")
        
        return response
    
    def _transform_response_v1(self, data: Any) -> Any:
        """Transform response for V1 compatibility."""
        if isinstance(data, dict):
            # V1 uses flat error structure
            if "error" in data and isinstance(data["error"], dict):
                error = data["error"]
                data = {
                    "error": error.get("message", "Unknown error"),
                    "error_code": error.get("code", "UNKNOWN")
                }
            
            # V1 uses different field names
            if "created_at" in data:
                data["created"] = data.pop("created_at")
            if "updated_at" in data:
                data["modified"] = data.pop("updated_at")
            
            # Recursively transform nested objects
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    data[key] = self._transform_response_v1(value)
        
        elif isinstance(data, list):
            return [self._transform_response_v1(item) for item in data]
        
        return data
    
    def _transform_response_v2(self, data: Any) -> Any:
        """Ensure V2 response format."""
        if isinstance(data, dict):
            # V2 uses structured error format
            if "error" in data and isinstance(data["error"], str):
                data = {
                    "error": {
                        "message": data["error"],
                        "code": data.get("error_code", "UNKNOWN"),
                        "details": {}
                    }
                }
        
        return data


class VersionedRoute:
    """Helper class for versioned route registration."""
    
    def __init__(self, path: str, versions: List[str] = None):
        self.path = path
        self.versions = versions or ["v1", "v2"]
    
    def get_paths(self) -> List[str]:
        """Get all versioned paths."""
        paths = []
        for version in self.versions:
            # URL path versioning
            paths.append(f"/api/{version}{self.path}")
        
        # Also support unversioned path (uses header/accept versioning)
        paths.append(f"/api{self.path}")
        
        return paths
    
    @staticmethod
    def deprecate(version: str, message: str):
        """Decorator to mark endpoint as deprecated."""
        def decorator(func):
            func._deprecated = {
                "version": version,
                "message": message
            }
            return func
        return decorator
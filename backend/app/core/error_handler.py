from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError
from typing import Union, Dict, Any, Optional, List
import traceback
import logging
import json
import time
from uuid import uuid4

from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)

class ErrorDetail:
    """Error detail structure for consistent error responses."""
    def __init__(
        self, 
        code: str, 
        message: str, 
        details: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_id: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.details = details
        self.error_id = error_id or str(uuid4())
        self.timestamp = int(time.time())
    
    def to_dict(self) -> Dict[str, Any]:
        error_dict = {
            "code": self.code,
            "message": self.message,
            "error_id": self.error_id,
            "timestamp": self.timestamp
        }
        if self.details:
            error_dict["details"] = self.details
        return error_dict

class APIError(Exception):
    """Base exception for all API errors."""
    def __init__(
        self, 
        status_code: int, 
        code: str, 
        message: str, 
        details: Optional[Union[str, List[Dict[str, Any]]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.status_code = status_code
        self.error_detail = ErrorDetail(code, message, details)
        self.headers = headers
        super().__init__(message)

class BadRequestError(APIError):
    """400 Bad Request error."""
    def __init__(
        self, 
        message: str = "Invalid request data",
        code: str = "BAD_REQUEST", 
        details: Optional[Union[str, List[Dict[str, Any]]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status.HTTP_400_BAD_REQUEST, code, message, details, headers)

class UnauthorizedError(APIError):
    """401 Unauthorized error."""
    def __init__(
        self, 
        message: str = "Authentication required",
        code: str = "UNAUTHORIZED", 
        details: Optional[Union[str, List[Dict[str, Any]]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status.HTTP_401_UNAUTHORIZED, code, message, details, headers)

class ForbiddenError(APIError):
    """403 Forbidden error."""
    def __init__(
        self, 
        message: str = "Insufficient permissions",
        code: str = "FORBIDDEN", 
        details: Optional[Union[str, List[Dict[str, Any]]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status.HTTP_403_FORBIDDEN, code, message, details, headers)

class NotFoundError(APIError):
    """404 Not Found error."""
    def __init__(
        self, 
        message: str = "Resource not found",
        code: str = "NOT_FOUND", 
        details: Optional[Union[str, List[Dict[str, Any]]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status.HTTP_404_NOT_FOUND, code, message, details, headers)

class ConflictError(APIError):
    """409 Conflict error."""
    def __init__(
        self, 
        message: str = "Resource conflict",
        code: str = "CONFLICT", 
        details: Optional[Union[str, List[Dict[str, Any]]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status.HTTP_409_CONFLICT, code, message, details, headers)

class TooManyRequestsError(APIError):
    """429 Too Many Requests error."""
    def __init__(
        self, 
        message: str = "Rate limit exceeded",
        code: str = "TOO_MANY_REQUESTS", 
        details: Optional[Union[str, List[Dict[str, Any]]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status.HTTP_429_TOO_MANY_REQUESTS, code, message, details, headers)

class ServerError(APIError):
    """500 Internal Server Error."""
    def __init__(
        self, 
        message: str = "Internal server error",
        code: str = "SERVER_ERROR", 
        details: Optional[Union[str, List[Dict[str, Any]]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, code, message, details, headers)

class ServiceUnavailableError(APIError):
    """503 Service Unavailable error."""
    def __init__(
        self, 
        message: str = "Service temporarily unavailable",
        code: str = "SERVICE_UNAVAILABLE", 
        details: Optional[Union[str, List[Dict[str, Any]]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status.HTTP_503_SERVICE_UNAVAILABLE, code, message, details, headers)

async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handler for APIError exceptions."""
    error_dict = exc.error_detail.to_dict()
    
    # Log based on severity
    log_message = f"API Error: {exc.error_detail.code} - {exc.error_detail.message}"
    request_details = {
        "request_id": getattr(request.state, "request_id", "unknown"),
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else "unknown",
        "error_id": exc.error_detail.error_id
    }
    
    if 400 <= exc.status_code < 500:
        logger.warning(f"{log_message} - {json.dumps(request_details)}")
    else:
        logger.error(f"{log_message} - {json.dumps(request_details)}")
        
        # Only log full details for server errors
        if settings.DEBUG:
            logger.error(f"Error details: {exc.error_detail.details}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_dict},
        headers=exc.headers
    )

async def validation_error_handler(request: Request, exc: Union[RequestValidationError, ValidationError]) -> JSONResponse:
    """Handler for validation errors."""
    error_id = str(uuid4())
    errors = exc.errors()
    
    # Format validation errors
    formatted_errors = []
    for error in errors:
        formatted_errors.append({
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", "")
        })
    
    error_detail = ErrorDetail(
        code="VALIDATION_ERROR",
        message="Request validation error",
        details=formatted_errors,
        error_id=error_id
    )
    
    # Log validation errors
    logger.warning(
        f"Validation Error: {error_id} - "
        f"Path: {request.url.path} - "
        f"Method: {request.method} - "
        f"Errors: {json.dumps(formatted_errors)}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": error_detail.to_dict()}
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handler for HTTP exceptions."""
    error_id = str(uuid4())
    
    error_detail = ErrorDetail(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        error_id=error_id
    )
    
    # Log based on severity
    log_message = f"HTTP Exception {exc.status_code}: {exc.detail}"
    request_details = {
        "request_id": getattr(request.state, "request_id", "unknown"),
        "method": request.method,
        "url": str(request.url),
        "error_id": error_id
    }
    
    if 400 <= exc.status_code < 500:
        logger.warning(f"{log_message} - {json.dumps(request_details)}")
    else:
        logger.error(f"{log_message} - {json.dumps(request_details)}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_detail.to_dict()},
        headers=exc.headers
    )

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for all unhandled exceptions."""
    error_id = str(uuid4())
    
    # Create sanitized error message for production
    if settings.DEBUG:
        error_message = str(exc)
        error_details = traceback.format_exc()
    else:
        error_message = "An unexpected error occurred"
        error_details = None
    
    error_detail = ErrorDetail(
        code="INTERNAL_SERVER_ERROR",
        message=error_message,
        details=error_details,
        error_id=error_id
    )
    
    # Log exception with stack trace
    logger.error(
        f"Unhandled Exception: {error_id} - "
        f"Path: {request.url.path} - "
        f"Method: {request.method} - "
        f"Error: {str(exc)}"
    )
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": error_detail.to_dict()}
    )

def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler) 
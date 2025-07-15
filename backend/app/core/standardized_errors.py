"""
Standardized error handling system for consistent error responses across all services.
Provides a unified approach to error handling, logging, and client responses.
"""

from typing import Optional, Dict, Any, List, Union
from enum import Enum
from datetime import datetime
import traceback
import sys
from functools import wraps
import asyncio

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.app.core.logger import logger


class ErrorCategory(str, Enum):
    """Categories of errors for better organization and handling."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    PAYMENT = "payment"
    RATE_LIMIT = "rate_limit"
    INTERNAL = "internal"
    CONFIGURATION = "configuration"


class ErrorSeverity(str, Enum):
    """Error severity levels for proper alerting and monitoring."""
    LOW = "low"        # Log only
    MEDIUM = "medium"  # Log and monitor
    HIGH = "high"      # Alert team
    CRITICAL = "critical"  # Page on-call


class StandardError(Exception):
    """Base exception class for all application errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        """
        Initialize standard error.
        
        Args:
            message: Internal error message for logging
            error_code: Unique error code for this error type
            status_code: HTTP status code to return
            category: Error category for grouping
            severity: Error severity for alerting
            details: Additional error details
            user_message: User-friendly message (defaults to generic)
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.user_message = user_message or self._get_default_user_message()
        self.timestamp = datetime.utcnow()
        self.trace_id = None  # Set by middleware
        
        super().__init__(self.message)
    
    def _get_default_user_message(self) -> str:
        """Get default user-friendly message based on category."""
        messages = {
            ErrorCategory.VALIDATION: "Invalid input provided. Please check your request.",
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please log in again.",
            ErrorCategory.AUTHORIZATION: "You don't have permission to perform this action.",
            ErrorCategory.NOT_FOUND: "The requested resource was not found.",
            ErrorCategory.CONFLICT: "This action conflicts with existing data.",
            ErrorCategory.EXTERNAL_SERVICE: "An external service is temporarily unavailable.",
            ErrorCategory.DATABASE: "A database error occurred. Please try again.",
            ErrorCategory.PAYMENT: "Payment processing failed. Please try again.",
            ErrorCategory.RATE_LIMIT: "Too many requests. Please slow down.",
            ErrorCategory.INTERNAL: "An unexpected error occurred. Please try again later.",
            ErrorCategory.CONFIGURATION: "System configuration error. Please contact support."
        }
        return messages.get(self.category, messages[ErrorCategory.INTERNAL])
    
    def to_dict(self, include_internal: bool = False) -> Dict[str, Any]:
        """Convert error to dictionary for response."""
        error_dict = {
            "error": {
                "code": self.error_code,
                "message": self.user_message,
                "category": self.category.value,
                "timestamp": self.timestamp.isoformat(),
                "trace_id": self.trace_id
            }
        }
        
        # Add details if not sensitive
        safe_details = {k: v for k, v in self.details.items() 
                       if not k.startswith("_")}
        if safe_details:
            error_dict["error"]["details"] = safe_details
        
        # Include internal details in development
        if include_internal:
            error_dict["error"]["internal"] = {
                "message": self.message,
                "severity": self.severity.value,
                "status_code": self.status_code
            }
        
        return error_dict


# Specific error classes for common scenarios

class ValidationError(StandardError):
    """Input validation errors."""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details=details,
            **kwargs
        )


class AuthenticationError(StandardError):
    """Authentication failures."""
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTH_FAILED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class AuthorizationError(StandardError):
    """Authorization failures."""
    def __init__(self, message: str = "Insufficient permissions", resource: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if resource:
            details["resource"] = resource
            
        super().__init__(
            message=message,
            error_code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            **kwargs
        )


class NotFoundError(StandardError):
    """Resource not found errors."""
    def __init__(self, resource: str, identifier: Optional[Union[str, int]] = None, **kwargs):
        details = {"resource": resource}
        if identifier:
            details["identifier"] = str(identifier)
            
        super().__init__(
            message=f"{resource} not found",
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            category=ErrorCategory.NOT_FOUND,
            severity=ErrorSeverity.LOW,
            details=details,
            user_message=f"The requested {resource.lower()} was not found.",
            **kwargs
        )


class ConflictError(StandardError):
    """Resource conflict errors."""
    def __init__(self, message: str, resource: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if resource:
            details["resource"] = resource
            
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            category=ErrorCategory.CONFLICT,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            **kwargs
        )


class ExternalServiceError(StandardError):
    """External service failures."""
    def __init__(self, service: str, message: str, **kwargs):
        super().__init__(
            message=f"{service}: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            details={"service": service},
            user_message="A required service is temporarily unavailable. Please try again later.",
            **kwargs
        )


class DatabaseError(StandardError):
    """Database operation failures."""
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if operation:
            details["operation"] = operation
            
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            details=details,
            **kwargs
        )


class PaymentError(StandardError):
    """Payment processing errors."""
    def __init__(self, message: str, payment_method: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if payment_method:
            details["payment_method"] = payment_method
            
        super().__init__(
            message=message,
            error_code="PAYMENT_ERROR",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            category=ErrorCategory.PAYMENT,
            severity=ErrorSeverity.HIGH,
            details=details,
            **kwargs
        )


class RateLimitError(StandardError):
    """Rate limit exceeded errors."""
    def __init__(self, retry_after: int, limit: Optional[int] = None, **kwargs):
        details = {"retry_after": retry_after}
        if limit:
            details["limit"] = limit
            
        super().__init__(
            message="Rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.LOW,
            details=details,
            user_message=f"Too many requests. Please try again in {retry_after} seconds.",
            **kwargs
        )


# Error handler decorator

def handle_errors(
    default_error_code: str = "INTERNAL_ERROR",
    default_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    log_errors: bool = True,
    include_traceback: bool = False
):
    """
    Decorator for standardized error handling in route handlers.
    
    Usage:
        @router.get("/endpoint")
        @handle_errors(default_error_code="FETCH_FAILED")
        async def get_endpoint():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except StandardError as e:
                # Already a standard error, just log and re-raise
                if log_errors:
                    _log_error(e)
                raise
            except HTTPException as e:
                # Convert FastAPI exception to standard error
                std_error = StandardError(
                    message=str(e.detail),
                    error_code=default_error_code,
                    status_code=e.status_code,
                    user_message=str(e.detail)
                )
                if log_errors:
                    _log_error(std_error)
                raise std_error
            except Exception as e:
                # Unexpected error
                std_error = StandardError(
                    message=str(e),
                    error_code=default_error_code,
                    status_code=default_status,
                    severity=ErrorSeverity.HIGH,
                    details={"type": type(e).__name__}
                )
                
                if include_traceback:
                    std_error.details["traceback"] = traceback.format_exc()
                
                if log_errors:
                    _log_error(std_error, include_traceback=True)
                
                raise std_error
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except StandardError as e:
                if log_errors:
                    _log_error(e)
                raise
            except Exception as e:
                std_error = StandardError(
                    message=str(e),
                    error_code=default_error_code,
                    status_code=default_status,
                    severity=ErrorSeverity.HIGH
                )
                if log_errors:
                    _log_error(std_error, include_traceback=True)
                raise std_error
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def _log_error(error: StandardError, include_traceback: bool = False):
    """Log error with appropriate level based on severity."""
    log_data = {
        "error_code": error.error_code,
        "category": error.category.value,
        "severity": error.severity.value,
        "message": error.message,
        "details": error.details,
        "trace_id": error.trace_id
    }
    
    if include_traceback:
        log_data["traceback"] = traceback.format_exc()
    
    if error.severity == ErrorSeverity.CRITICAL:
        logger.critical(f"Critical error: {error.error_code}", extra=log_data)
    elif error.severity == ErrorSeverity.HIGH:
        logger.error(f"Error: {error.error_code}", extra=log_data)
    elif error.severity == ErrorSeverity.MEDIUM:
        logger.warning(f"Warning: {error.error_code}", extra=log_data)
    else:
        logger.info(f"Info: {error.error_code}", extra=log_data)


# Global error handler for FastAPI

async def global_error_handler(request: Request, exc: StandardError) -> JSONResponse:
    """
    Global error handler for StandardError exceptions.
    Add to FastAPI app: app.add_exception_handler(StandardError, global_error_handler)
    """
    # Add trace ID from request if available
    if hasattr(request.state, "trace_id"):
        exc.trace_id = request.state.trace_id
    
    # Include internal details in development
    include_internal = request.app.debug or request.app.state.environment == "development"
    
    # Add CORS headers if needed
    headers = {}
    if hasattr(request.state, "cors_headers"):
        headers.update(request.state.cors_headers)
    
    # Add retry-after header for rate limits
    if exc.category == ErrorCategory.RATE_LIMIT and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(include_internal=include_internal),
        headers=headers
    )


# Error aggregation for batch operations

class ErrorCollector:
    """Collect errors during batch operations."""
    
    def __init__(self, continue_on_error: bool = True):
        self.errors: List[StandardError] = []
        self.continue_on_error = continue_on_error
    
    def add(self, error: StandardError):
        """Add error to collection."""
        self.errors.append(error)
        if not self.continue_on_error:
            raise error
    
    def has_errors(self) -> bool:
        """Check if any errors collected."""
        return len(self.errors) > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of collected errors."""
        if not self.errors:
            return {"total": 0, "errors": []}
        
        return {
            "total": len(self.errors),
            "by_category": self._group_by_category(),
            "by_severity": self._group_by_severity(),
            "errors": [e.to_dict() for e in self.errors[:10]]  # First 10
        }
    
    def _group_by_category(self) -> Dict[str, int]:
        """Group errors by category."""
        counts = {}
        for error in self.errors:
            counts[error.category.value] = counts.get(error.category.value, 0) + 1
        return counts
    
    def _group_by_severity(self) -> Dict[str, int]:
        """Group errors by severity."""
        counts = {}
        for error in self.errors:
            counts[error.severity.value] = counts.get(error.severity.value, 0) + 1
        return counts
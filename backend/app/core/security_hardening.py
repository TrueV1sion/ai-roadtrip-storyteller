"""
Security hardening utilities and middleware for AI Road Trip Storyteller
Implements OWASP best practices and security controls
"""

import re
import html
import secrets
import hashlib
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import bleach
from sqlalchemy import text
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class SecurityHardening:
    """Comprehensive security hardening utilities"""
    
    # SQL injection prevention patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
        r"(--|\||;|\/\*|\*\/|xp_|sp_)",
        r"(\b(and|or)\b\s*\d*\s*=\s*\d*)",
        r"('|\"|`)((\s*)(\b(or|and)\b)(\s*)(\d*\s*=\s*\d*))",
    ]
    
    # XSS prevention - allowed tags and attributes
    ALLOWED_TAGS = [
        'p', 'br', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'strong', 'em', 'u', 'i', 'b', 'a', 'ul', 'ol', 'li', 'blockquote'
    ]
    
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        'span': ['class'],
        'div': ['class'],
    }
    
    # File upload restrictions
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @staticmethod
    def sanitize_input(value: Any, input_type: str = "text") -> Any:
        """
        Sanitize user input based on type
        
        Args:
            value: Input value to sanitize
            input_type: Type of input (text, html, filename, etc.)
            
        Returns:
            Sanitized value
        """
        if value is None:
            return None
            
        if isinstance(value, str):
            # Remove null bytes
            value = value.replace('\x00', '')
            
            if input_type == "text":
                # Basic text sanitization
                value = value.strip()
                # Remove control characters
                value = ''.join(char for char in value if ord(char) > 31 or char == '\n')
                
            elif input_type == "html":
                # HTML sanitization using bleach
                value = bleach.clean(
                    value,
                    tags=SecurityHardening.ALLOWED_TAGS,
                    attributes=SecurityHardening.ALLOWED_ATTRIBUTES,
                    strip=True
                )
                
            elif input_type == "filename":
                # Filename sanitization
                value = re.sub(r'[^a-zA-Z0-9._-]', '_', value)
                value = value[:255]  # Max filename length
                
            elif input_type == "email":
                # Email validation and sanitization
                value = value.lower().strip()
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
                    raise ValueError("Invalid email format")
                    
            elif input_type == "phone":
                # Phone number sanitization
                value = re.sub(r'[^0-9+\-() ]', '', value)
                
        elif isinstance(value, (int, float)):
            # Numeric validation
            if input_type == "positive":
                if value < 0:
                    raise ValueError("Value must be positive")
            elif input_type == "percentage":
                if not 0 <= value <= 100:
                    raise ValueError("Percentage must be between 0 and 100")
                    
        return value
    
    @staticmethod
    def prevent_sql_injection(query: str, params: Dict[str, Any]) -> bool:
        """
        Check for potential SQL injection patterns
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            True if safe, raises exception if injection detected
        """
        # Check query string
        for pattern in SecurityHardening.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected in query: {query}")
                raise HTTPException(status_code=400, detail="Invalid query")
        
        # Check parameters
        for key, value in params.items():
            if isinstance(value, str):
                for pattern in SecurityHardening.SQL_INJECTION_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        logger.warning(f"Potential SQL injection in parameter {key}: {value}")
                        raise HTTPException(status_code=400, detail="Invalid input")
        
        return True
    
    @staticmethod
    def validate_file_upload(filename: str, file_content: bytes) -> bool:
        """
        Validate file uploads for security
        
        Args:
            filename: Name of uploaded file
            file_content: File content bytes
            
        Returns:
            True if valid, raises exception if invalid
        """
        # Check file extension
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if f'.{ext}' not in SecurityHardening.ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="File type not allowed")
        
        # Check file size
        if len(file_content) > SecurityHardening.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Check file content matches extension (magic bytes)
        magic_bytes = {
            '.jpg': [b'\xff\xd8\xff'],
            '.jpeg': [b'\xff\xd8\xff'],
            '.png': [b'\x89PNG'],
            '.gif': [b'GIF87a', b'GIF89a'],
            '.pdf': [b'%PDF']
        }
        
        expected_headers = magic_bytes.get(f'.{ext}', [])
        if expected_headers:
            file_header = file_content[:10]
            if not any(file_header.startswith(header) for header in expected_headers):
                raise HTTPException(status_code=400, detail="File content does not match extension")
        
        return True
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
        """
        Hash sensitive data with salt
        
        Args:
            data: Data to hash
            salt: Optional salt (will generate if not provided)
            
        Returns:
            Hashed data with salt
        """
        if not salt:
            salt = secrets.token_hex(16)
        
        combined = f"{salt}{data}"
        hashed = hashlib.sha256(combined.encode()).hexdigest()
        
        return f"{salt}${hashed}"
    
    @staticmethod
    def verify_hashed_data(data: str, hashed_value: str) -> bool:
        """Verify data against hashed value"""
        try:
            salt, hash_part = hashed_value.split('$')
            return SecurityHardening.hash_sensitive_data(data, salt) == hashed_value
        except Exception as e:
            return False
    
    @staticmethod
    def mask_sensitive_data(data: str, data_type: str = "general") -> str:
        """
        Mask sensitive data for logging/display
        
        Args:
            data: Sensitive data to mask
            data_type: Type of data (email, phone, credit_card, etc.)
            
        Returns:
            Masked data
        """
        if not data:
            return data
            
        if data_type == "email":
            parts = data.split('@')
            if len(parts) == 2:
                name = parts[0]
                if len(name) > 2:
                    masked_name = name[0] + '*' * (len(name) - 2) + name[-1]
                else:
                    masked_name = '*' * len(name)
                return f"{masked_name}@{parts[1]}"
                
        elif data_type == "phone":
            if len(data) > 4:
                return '*' * (len(data) - 4) + data[-4:]
                
        elif data_type == "credit_card":
            if len(data) >= 12:
                return data[:4] + '*' * (len(data) - 8) + data[-4:]
                
        # Default masking
        if len(data) > 4:
            return data[:2] + '*' * (len(data) - 4) + data[-2:]
        else:
            return '*' * len(data)
    
    @staticmethod
    def validate_origin(request: Request, allowed_origins: List[str]) -> bool:
        """Validate request origin for CSRF protection"""
        origin = request.headers.get('origin', '')
        referer = request.headers.get('referer', '')
        
        # Check origin header
        if origin and origin in allowed_origins:
            return True
            
        # Check referer as fallback
        if referer:
            for allowed in allowed_origins:
                if referer.startswith(allowed):
                    return True
                    
        return False
    
    @staticmethod
    def rate_limit_key(request: Request, identifier: str = "ip") -> str:
        """Generate rate limiting key based on identifier"""
        if identifier == "ip":
            # Get real IP considering proxy headers
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip = forwarded.split(",")[0].strip()
            else:
                ip = request.client.host
            return f"rate_limit:ip:{ip}"
            
        elif identifier == "user":
            # Assumes user info is in request state
            user_id = getattr(request.state, "user_id", "anonymous")
            return f"rate_limit:user:{user_id}"
            
        elif identifier == "endpoint":
            return f"rate_limit:endpoint:{request.url.path}"
            
        return f"rate_limit:general:{identifier}"
    
    @staticmethod
    def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data before logging"""
        sensitive_fields = [
            'password', 'token', 'api_key', 'secret', 'credit_card',
            'ssn', 'pin', 'cvv', 'authorization'
        ]
        
        sanitized = {}
        for key, value in data.items():
            if any(field in key.lower() for field in sensitive_fields):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = SecurityHardening.sanitize_log_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    SecurityHardening.sanitize_log_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
                
        return sanitized


class SecurityMiddleware:
    """Security middleware for FastAPI"""
    
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, request: Request, call_next):
        # Add security headers
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Remove sensitive headers
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)
        
        return response


def create_security_error_handler(app):
    """Create custom error handlers for security"""
    
    @app.exception_handler(400)
    async def bad_request_handler(request: Request, exc: HTTPException):
        # Don't reveal internal error details
        return JSONResponse(
            status_code=400,
            content={"detail": "Bad request"}
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: Exception):
        # Log the actual error
        logger.error(f"Internal error: {str(exc)}", exc_info=True)
        
        # Return generic error to client
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


# Input validation schemas
class InputValidation:
    """Common input validation patterns"""
    
    # Regex patterns for validation
    PATTERNS = {
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'phone': re.compile(r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{4,6}$'),
        'url': re.compile(r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'),
        'alphanumeric': re.compile(r'^[a-zA-Z0-9]+$'),
        'safe_string': re.compile(r'^[a-zA-Z0-9\s\-_\.]+$'),
        'uuid': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE),
    }
    
    @classmethod
    def validate(cls, value: str, pattern_name: str) -> bool:
        """Validate input against pattern"""
        pattern = cls.PATTERNS.get(pattern_name)
        if pattern:
            return bool(pattern.match(value))
        return False
    
    @classmethod
    def validate_length(cls, value: str, min_length: int = 0, max_length: int = 1000) -> bool:
        """Validate string length"""
        return min_length <= len(value) <= max_length
    
    @classmethod
    def validate_numeric_range(cls, value: Union[int, float], min_val: float = float('-inf'), max_val: float = float('inf')) -> bool:
        """Validate numeric range"""
        return min_val <= value <= max_val
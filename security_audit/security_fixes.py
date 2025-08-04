#!/usr/bin/env python3
"""
Security Fixes Implementation for AI Road Trip Storyteller
Patches for common vulnerabilities found during security audit
"""

import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import secrets
import re
import hashlib
from functools import wraps
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class SecurityFixes:
    """Collection of security fixes for common vulnerabilities"""
    
    # 1. Input Validation Fixes
    @staticmethod
    def sanitize_input(input_string: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not input_string:
            return ""
            
        # Truncate to max length
        input_string = input_string[:max_length]
        
        # Remove null bytes
        input_string = input_string.replace('\x00', '')
        
        # Escape special characters for SQL
        sql_escape_chars = {
            "'": "''",
            '"': '""',
            '\\': '\\\\',
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t'
        }
        
        for char, escaped in sql_escape_chars.items():
            input_string = input_string.replace(char, escaped)
            
        return input_string
        
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        return bool(email_pattern.match(email)) and len(email) <= 254
        
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password meets security requirements"""
        errors = []
        
        if len(password) < 12:
            errors.append("Password must be at least 12 characters long")
            
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
            
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
            
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
            
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
            
        # Check for common passwords
        common_passwords = [
            "password", "123456", "password123", "admin", "letmein",
            "welcome", "monkey", "dragon", "baseball", "iloveyou"
        ]
        
        if password.lower() in common_passwords:
            errors.append("Password is too common")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": "strong" if len(errors) == 0 else "weak"
        }
        
    # 2. XSS Prevention
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters to prevent XSS"""
        if not text:
            return ""
            
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
            ">": "&gt;",
            "<": "&lt;",
            "/": "&#x2F;",
            "`": "&#x60;",
            "=": "&#x3D;"
        }
        
        for char, escaped in html_escape_table.items():
            text = text.replace(char, escaped)
            
        return text
        
    @staticmethod
    def sanitize_json_output(data: Any) -> Any:
        """Recursively sanitize JSON output to prevent XSS"""
        if isinstance(data, str):
            return SecurityFixes.escape_html(data)
        elif isinstance(data, dict):
            return {k: SecurityFixes.sanitize_json_output(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [SecurityFixes.sanitize_json_output(item) for item in data]
        else:
            return data
            
    # 3. CSRF Protection Enhancement
    @staticmethod
    def generate_csrf_token(user_id: str, secret_key: str) -> str:
        """Generate a secure CSRF token tied to user session"""
        # Include timestamp for token expiration
        timestamp = str(int(time.time()))
        
        # Create token with user ID and timestamp
        token_data = f"{user_id}:{timestamp}:{secrets.token_hex(16)}"
        
        # Create HMAC signature
        signature = hashlib.sha256(
            f"{token_data}:{secret_key}".encode()
        ).hexdigest()
        
        return f"{token_data}:{signature}"
        
    @staticmethod
    def verify_csrf_token(token: str, user_id: str, secret_key: str, 
                         max_age: int = 3600) -> bool:
        """Verify CSRF token with expiration check"""
        try:
            parts = token.split(":")
            if len(parts) != 4:
                return False
                
            token_user_id, timestamp, random_part, signature = parts
            
            # Check user ID matches
            if token_user_id != user_id:
                return False
                
            # Check token age
            token_age = int(time.time()) - int(timestamp)
            if token_age > max_age:
                return False
                
            # Verify signature
            token_data = f"{token_user_id}:{timestamp}:{random_part}"
            expected_signature = hashlib.sha256(
                f"{token_data}:{secret_key}".encode()
            ).hexdigest()
            
            return secrets.compare_digest(signature, expected_signature)
            
        except Exception:
            return False
            
    # 4. SQL Injection Prevention
    @staticmethod
    def create_parameterized_query(query_template: str, params: Dict[str, Any]) -> tuple:
        """Create parameterized query to prevent SQL injection"""
        # Replace named parameters with positional ones
        query = query_template
        values = []
        
        for param_name, param_value in params.items():
            placeholder = f":{param_name}"
            if placeholder in query:
                query = query.replace(placeholder, "%s", 1)
                values.append(param_value)
                
        return query, tuple(values)
        
    @staticmethod
    def validate_table_name(table_name: str) -> bool:
        """Validate table name to prevent SQL injection in dynamic queries"""
        # Only allow alphanumeric and underscore
        return bool(re.match(r'^[a-zA-Z0-9_]+$', table_name))
        
    # 5. Authentication Security Enhancements
    @staticmethod
    def hash_password_secure(password: str, rounds: int = 12) -> str:
        """Hash password with bcrypt using appropriate cost factor"""
        import bcrypt
        
        # Generate salt with specified rounds
        salt = bcrypt.gensalt(rounds=rounds)
        
        # Hash password
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        return hashed.decode('utf-8')
        
    @staticmethod
    def implement_account_lockout(user_id: str, failed_attempts: int, 
                                lockout_threshold: int = 5) -> Dict[str, Any]:
        """Implement account lockout after failed login attempts"""
        if failed_attempts >= lockout_threshold:
            lockout_duration = min(2 ** (failed_attempts - lockout_threshold), 3600)  # Max 1 hour
            lockout_until = datetime.now() + timedelta(seconds=lockout_duration)
            
            return {
                "locked": True,
                "lockout_until": lockout_until,
                "remaining_attempts": 0
            }
        else:
            return {
                "locked": False,
                "lockout_until": None,
                "remaining_attempts": lockout_threshold - failed_attempts
            }
            
    # 6. Session Security Fixes
    @staticmethod
    def generate_secure_session_id() -> str:
        """Generate cryptographically secure session ID"""
        # Use 32 bytes (256 bits) of randomness
        return secrets.token_urlsafe(32)
        
    @staticmethod
    def rotate_session_on_login(old_session_id: str) -> str:
        """Rotate session ID on login to prevent fixation"""
        # Always generate new session ID on login
        new_session_id = SecurityFixes.generate_secure_session_id()
        
        # In real implementation, would migrate session data here
        # and invalidate old session
        
        return new_session_id
        
    # 7. Rate Limiting Implementation
    class RateLimiter:
        """Simple in-memory rate limiter"""
        
        def __init__(self):
            self.requests = {}
            
        def is_allowed(self, identifier: str, max_requests: int = 60, 
                      window_seconds: int = 60) -> bool:
            """Check if request is allowed under rate limit"""
            now = time.time()
            
            # Clean old entries
            self.requests = {
                k: [t for t in v if now - t < window_seconds]
                for k, v in self.requests.items()
            }
            
            # Get request times for identifier
            request_times = self.requests.get(identifier, [])
            
            # Check if under limit
            if len(request_times) >= max_requests:
                return False
                
            # Add current request
            request_times.append(now)
            self.requests[identifier] = request_times
            
            return True
            
    # 8. File Upload Security
    @staticmethod
    def validate_file_upload(filename: str, content: bytes, 
                           allowed_extensions: List[str] = None,
                           max_size: int = 10 * 1024 * 1024) -> Dict[str, Any]:
        """Validate file upload for security"""
        errors = []
        
        # Default allowed extensions
        if allowed_extensions is None:
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.txt']
            
        # Check file size
        if len(content) > max_size:
            errors.append(f"File size exceeds maximum of {max_size} bytes")
            
        # Sanitize filename
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        if safe_filename != filename:
            errors.append("Filename contains invalid characters")
            
        # Check extension
        _, ext = os.path.splitext(filename.lower())
        if ext not in allowed_extensions:
            errors.append(f"File type {ext} not allowed")
            
        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            errors.append("Path traversal attempt detected")
            
        # Check file content matches extension
        import magic
        try:
            file_type = magic.from_buffer(content, mime=True)
            expected_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.pdf': 'application/pdf',
                '.txt': 'text/plain'
            }
            
            if ext in expected_types and not file_type.startswith(expected_types[ext]):
                errors.append(f"File content doesn't match extension {ext}")
        except:
            pass
            
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "safe_filename": safe_filename
        }
        
    # 9. API Security Headers
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get recommended security headers"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' https://api.spotify.com https://maps.googleapis.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "accelerometer=(), camera=(), geolocation=(self), "
                "gyroscope=(), magnetometer=(), microphone=(self), "
                "payment=(), usb=()"
            )
        }
        
    # 10. Secure Random Token Generation
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
        
    @staticmethod
    def generate_api_key() -> str:
        """Generate secure API key"""
        # Format: prefix_randomtoken
        prefix = "rtsk"  # Road Trip Secret Key
        token = secrets.token_urlsafe(32)
        return f"{prefix}_{token}"
        
    # 11. Secure Configuration
    @staticmethod
    def validate_environment_config() -> List[str]:
        """Validate environment configuration for security"""
        issues = []
        
        # Check for default/weak secrets
        weak_secrets = ["secret", "password", "123456", "admin", "default"]
        
        secret_key = os.getenv("SECRET_KEY", "")
        if not secret_key:
            issues.append("SECRET_KEY not set")
        elif len(secret_key) < 32:
            issues.append("SECRET_KEY too short (minimum 32 characters)")
        elif secret_key.lower() in weak_secrets:
            issues.append("SECRET_KEY is weak/default")
            
        # Check database URL doesn't contain password
        db_url = os.getenv("DATABASE_URL", "")
        if "password" in db_url and "@" in db_url:
            issues.append("Database password exposed in DATABASE_URL")
            
        # Check debug mode
        if os.getenv("DEBUG", "false").lower() == "true":
            issues.append("DEBUG mode enabled in production")
            
        # Check HTTPS enforcement
        if os.getenv("FORCE_HTTPS", "true").lower() != "true":
            issues.append("HTTPS not enforced")
            
        return issues
        
    # 12. Logging Security
    @staticmethod
    def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data before logging"""
        sensitive_fields = [
            "password", "token", "api_key", "secret", "credit_card",
            "ssn", "session_id", "authorization"
        ]
        
        sanitized = data.copy()
        
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "[REDACTED]"
                
        # Recursively sanitize nested dictionaries
        for key, value in sanitized.items():
            if isinstance(value, dict):
                sanitized[key] = SecurityFixes.sanitize_log_data(value)
                
        return sanitized


# FastAPI Security Middleware
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import json

def add_security_middleware(app: FastAPI):
    """Add security middleware to FastAPI app"""
    
    rate_limiter = SecurityFixes.RateLimiter()
    
    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        # 1. Add security headers
        response = await call_next(request)
        
        for header, value in SecurityFixes.get_security_headers().items():
            response.headers[header] = value
            
        # 2. Rate limiting
        client_ip = request.client.host
        endpoint = f"{request.method}:{request.url.path}"
        
        if not rate_limiter.is_allowed(f"{client_ip}:{endpoint}"):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "60"}
            )
            
        # 3. Request size limiting
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > 10 * 1024 * 1024:  # 10MB limit
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request too large"}
                )
                
        return response
        
    @app.exception_handler(Exception)
    async def security_exception_handler(request: Request, exc: Exception):
        """Secure exception handler that doesn't leak information"""
        # Log the actual error securely
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        
        # Return generic error to client
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


# Input validation decorators
def validate_request(schema):
    """Decorator to validate request data against schema"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if request:
                try:
                    data = await request.json()
                    # Validate against schema
                    errors = validate_against_schema(data, schema)
                    if errors:
                        return JSONResponse(
                            status_code=400,
                            content={"detail": "Validation error", "errors": errors}
                        )
                except Exception:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Invalid request data"}
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Basic schema validation"""
    errors = []
    
    for field, rules in schema.items():
        value = data.get(field)
        
        # Required field check
        if rules.get("required", False) and value is None:
            errors.append(f"{field} is required")
            continue
            
        if value is not None:
            # Type check
            expected_type = rules.get("type")
            if expected_type and not isinstance(value, expected_type):
                errors.append(f"{field} must be of type {expected_type.__name__}")
                
            # Length check
            if "max_length" in rules and isinstance(value, str):
                if len(value) > rules["max_length"]:
                    errors.append(f"{field} exceeds maximum length of {rules['max_length']}")
                    
            # Pattern check
            if "pattern" in rules and isinstance(value, str):
                import re
                if not re.match(rules["pattern"], value):
                    errors.append(f"{field} does not match required pattern")
                    
    return errors


# Example usage
if __name__ == "__main__":
    # Test input sanitization
    print("Testing input sanitization:")
    dangerous_input = "'; DROP TABLE users; --"
    safe_input = SecurityFixes.sanitize_input(dangerous_input)
    print(f"Original: {dangerous_input}")
    print(f"Sanitized: {safe_input}")
    
    # Test password validation
    print("\nTesting password validation:")
    passwords = ["weak", "StrongP@ssw0rd!", "password123"]
    for pwd in passwords:
        result = SecurityFixes.validate_password_strength(pwd)
        print(f"{pwd}: {result}")
        
    # Test XSS prevention
    print("\nTesting XSS prevention:")
    xss_input = "<script>alert('XSS')</script>"
    safe_output = SecurityFixes.escape_html(xss_input)
    print(f"Original: {xss_input}")
    print(f"Escaped: {safe_output}")
    
    # Test CSRF token
    print("\nTesting CSRF token:")
    user_id = "user123"
    secret = "very-secret-key"
    token = SecurityFixes.generate_csrf_token(user_id, secret)
    print(f"Generated token: {token}")
    print(f"Valid: {SecurityFixes.verify_csrf_token(token, user_id, secret)}")
    
    # Test secure token generation
    print("\nTesting secure token generation:")
    print(f"Session ID: {SecurityFixes.generate_secure_session_id()}")
    print(f"API Key: {SecurityFixes.generate_api_key()}")
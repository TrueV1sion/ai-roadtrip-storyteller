from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, Tuple
from passlib.context import CryptContext
from app.core.config import settings
from fastapi import HTTPException, status

# Import the new JWT manager
from app.core.jwt_manager import (
    jwt_manager,
    create_access_token as _create_access_token,
    create_refresh_token as _create_refresh_token,
    decode_token as _decode_token,
    validate_token as _validate_token,
    revoke_token as _revoke_token,
    get_token_subject as _get_token_subject,
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Re-export JWT settings for backward compatibility
ALGORITHM = settings.JWT_ALGORITHM


def create_token(
    subject: Union[str, Any],
    token_type: str,
    expires_delta: Optional[timedelta] = None,
    extras: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT token with specified type and expiration.
    Now delegates to the JWT manager for RS256 support.
    
    Args:
        subject: Token subject (usually user ID)
        token_type: Type of token (access or refresh)
        expires_delta: Optional expiration delta
        extras: Additional claims to include
        
    Returns:
        str: Encoded JWT token
    """
    return jwt_manager.create_token(
        subject=subject,
        token_type=token_type,
        expires_delta=expires_delta,
        extras=extras
    )


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token using RS256.
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Optional expiration delta
        
    Returns:
        str: Encoded JWT token
    """
    return _create_access_token(
        subject=subject,
        expires_delta=expires_delta
    )


def create_refresh_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token with longer expiration using RS256.
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Optional expiration delta
        
    Returns:
        str: Encoded JWT refresh token
    """
    return _create_refresh_token(
        subject=subject,
        expires_delta=expires_delta
    )


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token and validate it using RS256.
    
    Args:
        token: JWT token
        
    Returns:
        Optional[Dict[str, Any]]: Token payload or None if invalid
    """
    return _decode_token(token)


def get_token_subject(token: str) -> Optional[str]:
    """
    Extract the subject from a token.
    
    Args:
        token: JWT token
        
    Returns:
        Optional[str]: Token subject or None if invalid
    """
    return _get_token_subject(token)


def validate_token(token: str, expected_type: str) -> Optional[Dict[str, Any]]:
    """
    Validate a token and check its type.
    
    Args:
        token: JWT token
        expected_type: Expected token type
        
    Returns:
        Optional[Dict[str, Any]]: Token payload if valid
    """
    return _validate_token(token, expected_type)


def revoke_token(token: str) -> bool:
    """
    Revoke a token by adding it to the blacklist.
    
    Args:
        token: JWT token
        
    Returns:
        bool: True if token was revoked
    """
    return _revoke_token(token)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)
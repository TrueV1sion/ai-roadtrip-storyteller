from typing import Optional, Dict, Any
from pydantic import BaseModel

# Re-export 2FA schemas for convenience
from .two_factor import (
    TwoFactorSetupResponse,
    TwoFactorEnableRequest,
    TwoFactorVerifyRequest,
    TwoFactorDisableRequest,
    BackupCodesResponse,
    TwoFactorStatusResponse
)


class Token(BaseModel):
    """Token schema for authentication."""
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    requires_2fa: Optional[bool] = None
    partial_token: Optional[str] = None  # Used when 2FA is required
    

class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str
    

class TokenPayload(BaseModel):
    """Token payload schema."""
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None
    jti: Optional[str] = None


class TokenRevoke(BaseModel):
    """Schema for token revocation request."""
    token: str
    token_type_hint: Optional[str] = None  # access_token or refresh_token


class TwoFactorLogin(BaseModel):
    """Schema for completing login with 2FA."""
    partial_token: str
    code: str  # 6-digit TOTP or 8-digit backup code
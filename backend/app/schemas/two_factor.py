"""
Pydantic schemas for Two-Factor Authentication.
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class TwoFactorSetupResponse(BaseModel):
    """Response for 2FA setup initiation."""
    qr_code: str = Field(..., description="Base64 encoded QR code image")
    secret: str = Field(..., description="TOTP secret (for manual entry)")
    backup_codes: List[str] = Field(..., description="List of backup codes")
    setup_complete: bool = Field(False, description="Whether setup is complete")


class TwoFactorEnableRequest(BaseModel):
    """Request to enable 2FA with verification code."""
    code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$", 
                     description="6-digit TOTP code")
    
    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError('Code must contain only digits')
        return v


class TwoFactorVerifyRequest(BaseModel):
    """Request to verify 2FA during login."""
    session_id: str = Field(..., description="Session ID from login flow")
    user_id: str = Field(..., description="User ID from login flow")
    code: Optional[str] = Field(None, min_length=6, max_length=6, pattern="^[0-9]{6}$",
                               description="6-digit TOTP code")
    backup_code: Optional[str] = Field(None, pattern="^[0-9A-Z]{4}-[0-9A-Z]{4}$",
                                      description="Backup code in format XXXX-XXXX")
    
    @validator('code')
    def validate_code(cls, v):
        if v and not v.isdigit():
            raise ValueError('Code must contain only digits')
        return v
    
    @validator('backup_code')
    def validate_backup_code(cls, v):
        if v:
            v = v.upper()
            if not v.replace('-', '').isalnum():
                raise ValueError('Backup code must contain only alphanumeric characters')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "abc123",
                "user_id": "user-uuid",
                "code": "123456"
            }
        }


class TwoFactorDisableRequest(BaseModel):
    """Request to disable 2FA."""
    password: str = Field(..., min_length=8, description="User password for verification")
    
    class Config:
        schema_extra = {
            "example": {
                "password": "current_password"
            }
        }


class BackupCodesResponse(BaseModel):
    """Response containing backup codes."""
    backup_codes: List[str] = Field(..., description="List of backup codes")
    generated_at: str = Field(..., description="ISO timestamp of generation")
    
    class Config:
        schema_extra = {
            "example": {
                "backup_codes": [
                    "ABCD-1234",
                    "EFGH-5678",
                    "IJKL-9012"
                ],
                "generated_at": "2024-01-15T10:30:00Z"
            }
        }


class TwoFactorStatusResponse(BaseModel):
    """Response for 2FA status check."""
    enabled: bool = Field(..., description="Whether 2FA is enabled")
    enabled_at: Optional[str] = Field(None, description="ISO timestamp when enabled")
    last_used: Optional[str] = Field(None, description="ISO timestamp of last use")
    backup_codes_count: int = Field(..., description="Number of remaining backup codes")
    
    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "enabled_at": "2024-01-15T10:30:00Z",
                "last_used": "2024-01-15T14:20:00Z",
                "backup_codes_count": 8
            }
        }
"""
Schemas for password-related operations.
"""

from typing import Optional
from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=12, max_length=128, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordResetRequest(BaseModel):
    """Schema for requesting password reset."""
    email: EmailStr = Field(..., description="Email address for reset")


class PasswordResetConfirm(BaseModel):
    """Schema for confirming password reset."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=12, max_length=128, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordStrengthRequest(BaseModel):
    """Schema for checking password strength."""
    password: str = Field(..., description="Password to check")
    email: Optional[EmailStr] = Field(None, description="User email for context")
    name: Optional[str] = Field(None, description="User name for context")


class PasswordStrengthResponse(BaseModel):
    """Schema for password strength response."""
    score: int = Field(..., ge=0, le=100, description="Strength score 0-100")
    level: str = Field(..., description="Strength level")
    feedback: list[str] = Field(default_factory=list, description="Improvement suggestions")
    meets_requirements: bool = Field(..., description="Whether password meets all requirements")
    is_pwned: bool = Field(False, description="Whether password was found in breaches")
    pwned_count: int = Field(0, description="Number of times found in breaches")


class PasswordPolicyResponse(BaseModel):
    """Schema for password policy information."""
    min_length: int = Field(..., description="Minimum password length")
    max_length: int = Field(..., description="Maximum password length")
    require_uppercase: bool = Field(..., description="Require uppercase letters")
    require_lowercase: bool = Field(..., description="Require lowercase letters")
    require_numbers: bool = Field(..., description="Require numbers")
    require_special: bool = Field(..., description="Require special characters")
    special_chars: str = Field(..., description="Allowed special characters")
    password_expiry_days: int = Field(..., description="Password expiry in days (0=no expiry)")


class PasswordExpiryInfo(BaseModel):
    """Schema for password expiry information."""
    is_expired: bool = Field(..., description="Whether password has expired")
    expiry_date: Optional[datetime] = Field(None, description="Password expiry date")
    days_until_expiry: Optional[int] = Field(None, description="Days until password expires")
    last_changed: Optional[datetime] = Field(None, description="When password was last changed")
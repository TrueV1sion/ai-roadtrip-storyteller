"""
Comprehensive password policy module following OWASP guidelines.
Implements secure password validation, history tracking, and strength calculation.
"""

import re
import hashlib
import secrets
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import httpx
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.logger import get_logger
from app.core.cache import get_cache
from app.core.config import settings

logger = get_logger(__name__)

# Password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


class PasswordStrength(BaseModel):
    """Password strength assessment result."""
    score: int = Field(..., ge=0, le=100, description="Strength score 0-100")
    level: str = Field(..., description="Strength level: weak, fair, good, strong, excellent")
    feedback: List[str] = Field(default_factory=list, description="Improvement suggestions")
    meets_requirements: bool = Field(..., description="Whether password meets all requirements")
    details: Dict[str, bool] = Field(default_factory=dict, description="Detailed requirement checks")


class PasswordPolicyConfig(BaseModel):
    """Configuration for password policy."""
    min_length: int = Field(default=12, ge=8, description="Minimum password length")
    max_length: int = Field(default=128, le=256, description="Maximum password length")
    require_uppercase: bool = Field(default=True, description="Require uppercase letters")
    require_lowercase: bool = Field(default=True, description="Require lowercase letters")
    require_numbers: bool = Field(default=True, description="Require numeric characters")
    require_special: bool = Field(default=True, description="Require special characters")
    special_chars: str = Field(default="!@#$%^&*()_+-=[]{}|;:,.<>?", description="Allowed special characters")
    
    # Advanced requirements
    min_uppercase: int = Field(default=1, ge=0, description="Minimum uppercase letters")
    min_lowercase: int = Field(default=1, ge=0, description="Minimum lowercase letters")
    min_numbers: int = Field(default=1, ge=0, description="Minimum numeric characters")
    min_special: int = Field(default=1, ge=0, description="Minimum special characters")
    
    # Security features
    check_common_passwords: bool = Field(default=True, description="Check against common passwords")
    check_pwned_passwords: bool = Field(default=True, description="Check HaveIBeenPwned database")
    prevent_user_info: bool = Field(default=True, description="Prevent passwords containing user info")
    prevent_sequences: bool = Field(default=True, description="Prevent keyboard patterns and sequences")
    
    # Password history
    password_history_count: int = Field(default=5, ge=0, description="Number of previous passwords to check")
    min_password_age_days: int = Field(default=1, ge=0, description="Minimum days before password change")
    max_password_age_days: int = Field(default=90, ge=0, description="Maximum password age (0=no expiry)")
    
    # Account lockout
    max_failed_attempts: int = Field(default=5, ge=3, description="Failed attempts before lockout")
    lockout_duration_minutes: int = Field(default=30, ge=5, description="Account lockout duration")
    reset_failed_attempts_minutes: int = Field(default=30, ge=5, description="Time to reset failed counter")


class PasswordPolicy:
    """
    Comprehensive password policy implementation following OWASP guidelines.
    """
    
    def __init__(self, config: Optional[PasswordPolicyConfig] = None):
        self.config = config or PasswordPolicyConfig()
        self._common_passwords = None
        self._keyboard_patterns = [
            "qwerty", "asdfgh", "zxcvbn", "qwertyuiop", "asdfghjkl", "zxcvbnm",
            "123456", "234567", "345678", "456789", "567890",
            "abcdef", "bcdefg", "cdefgh", "defghi", "efghij"
        ]
        self.cache = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization of cache connection"""
        if not self._initialized:
            self.cache = await get_cache()
            self._initialized = True
    
    def _load_common_passwords(self) -> set:
        """Load common passwords list (top 10000)."""
        if self._common_passwords is None:
            # In production, load from file or database
            # For now, using a minimal set
            self._common_passwords = {
                "password", "123456", "password123", "admin", "letmein",
                "welcome", "monkey", "dragon", "baseball", "football",
                "qwerty", "abc123", "123456789", "12345678", "1234567",
                "sunshine", "master", "123123", "welcome123", "password1",
                "password123!", "admin123", "root", "toor", "pass",
                "test", "guest", "oracle", "changeme", "password1234"
            }
        return self._common_passwords
    
    def validate_password(
        self,
        password: str,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> PasswordStrength:
        """
        Validate password against policy requirements.
        
        Args:
            password: The password to validate
            user_email: User's email to check password doesn't contain it
            user_name: User's name to check password doesn't contain it
            
        Returns:
            PasswordStrength object with validation results
        """
        feedback = []
        details = {}
        score = 100  # Start with perfect score and deduct
        
        # Length checks
        if len(password) < self.config.min_length:
            feedback.append(f"Password must be at least {self.config.min_length} characters long")
            score -= 30
            details["min_length"] = False
        else:
            details["min_length"] = True
        
        if len(password) > self.config.max_length:
            feedback.append(f"Password must not exceed {self.config.max_length} characters")
            score -= 10
            details["max_length"] = False
        else:
            details["max_length"] = True
        
        # Character type checks
        uppercase_count = sum(1 for c in password if c.isupper())
        lowercase_count = sum(1 for c in password if c.islower())
        number_count = sum(1 for c in password if c.isdigit())
        special_count = sum(1 for c in password if c in self.config.special_chars)
        
        if self.config.require_uppercase and uppercase_count < self.config.min_uppercase:
            feedback.append(f"Password must contain at least {self.config.min_uppercase} uppercase letter(s)")
            score -= 15
            details["uppercase"] = False
        else:
            details["uppercase"] = True
        
        if self.config.require_lowercase and lowercase_count < self.config.min_lowercase:
            feedback.append(f"Password must contain at least {self.config.min_lowercase} lowercase letter(s)")
            score -= 15
            details["lowercase"] = False
        else:
            details["lowercase"] = True
        
        if self.config.require_numbers and number_count < self.config.min_numbers:
            feedback.append(f"Password must contain at least {self.config.min_numbers} number(s)")
            score -= 15
            details["numbers"] = False
        else:
            details["numbers"] = True
        
        if self.config.require_special and special_count < self.config.min_special:
            feedback.append(f"Password must contain at least {self.config.min_special} special character(s)")
            score -= 15
            details["special"] = False
        else:
            details["special"] = True
        
        # Check for common passwords
        if self.config.check_common_passwords:
            common_passwords = self._load_common_passwords()
            if password.lower() in common_passwords:
                feedback.append("This password is too common. Please choose a more unique password")
                score -= 40
                details["not_common"] = False
            else:
                details["not_common"] = True
        
        # Check for user information in password
        if self.config.prevent_user_info:
            contains_user_info = False
            
            if user_email:
                email_parts = user_email.lower().split('@')[0].split('.')
                for part in email_parts:
                    if len(part) > 3 and part in password.lower():
                        contains_user_info = True
                        break
            
            if user_name:
                name_parts = user_name.lower().split()
                for part in name_parts:
                    if len(part) > 3 and part in password.lower():
                        contains_user_info = True
                        break
            
            if contains_user_info:
                feedback.append("Password should not contain your name or email")
                score -= 20
                details["no_user_info"] = False
            else:
                details["no_user_info"] = True
        
        # Check for sequences and patterns
        if self.config.prevent_sequences:
            has_pattern = False
            password_lower = password.lower()
            
            # Check keyboard patterns
            for pattern in self._keyboard_patterns:
                if pattern in password_lower:
                    has_pattern = True
                    break
            
            # Check sequential characters
            for i in range(len(password) - 2):
                if ord(password[i]) + 1 == ord(password[i + 1]) == ord(password[i + 2]) - 1:
                    has_pattern = True
                    break
            
            if has_pattern:
                feedback.append("Password should not contain keyboard patterns or sequences")
                score -= 15
                details["no_patterns"] = False
            else:
                details["no_patterns"] = True
        
        # Calculate entropy bonus for length and variety
        if len(password) > 15:
            score = min(100, score + 5)
        if len(password) > 20:
            score = min(100, score + 5)
        
        # Determine strength level
        if score >= 90:
            level = "excellent"
        elif score >= 75:
            level = "strong"
        elif score >= 60:
            level = "good"
        elif score >= 40:
            level = "fair"
        else:
            level = "weak"
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        return PasswordStrength(
            score=score,
            level=level,
            feedback=feedback,
            meets_requirements=len(feedback) == 0,
            details=details
        )
    
    async def check_pwned_password(self, password: str) -> Tuple[bool, int]:
        """
        Check if password has been exposed in data breaches using HaveIBeenPwned API.
        
        Args:
            password: The password to check
            
        Returns:
            Tuple of (is_pwned, occurrence_count)
        """
        if not self.config.check_pwned_passwords:
            return False, 0
        
        await self._ensure_initialized()
        
        # Calculate SHA-1 hash
        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]
        
        # Check cache first
        cache_key = f"pwned_check:{prefix}"
        cached_result = await self.cache.get(cache_key) if self.cache else None
        
        if cached_result:
            hashes = cached_result.split('\n')
        else:
            try:
                # Query HaveIBeenPwned API
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://api.pwnedpasswords.com/range/{prefix}",
                        headers={"User-Agent": "RoadTrip-Security-Check"},
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        hashes = response.text.split('\n')
                        # Cache for 24 hours
                        if self.cache:
                            await self.cache.setex(cache_key, 86400, response.text)
                    else:
                        logger.warning(f"HaveIBeenPwned API returned status {response.status_code}")
                        return False, 0
                        
            except Exception as e:
                logger.error(f"Error checking pwned passwords: {e}")
                # Fail open - don't block user if service is down
                return False, 0
        
        # Check if our hash suffix is in the results
        for hash_entry in hashes:
            if ':' in hash_entry:
                hash_suffix, count = hash_entry.split(':')
                if hash_suffix.strip() == suffix:
                    return True, int(count)
        
        return False, 0
    
    async def save_password_history(
        self,
        db: Session,
        user_id: str,
        password_hash: str
    ) -> None:
        """
        Save password to user's password history.
        
        Args:
            db: Database session
            user_id: User ID
            password_hash: Hashed password
        """
        from app.models.password_history import PasswordHistory
        
        try:
            # Create new password history entry
            history_entry = PasswordHistory(
                user_id=user_id,
                password_hash=password_hash,
                created_at=datetime.utcnow()
            )
            db.add(history_entry)
            
            # Clean up old entries beyond history limit
            if self.config.password_history_count > 0:
                # Get all history entries for user
                all_entries = db.query(PasswordHistory)\
                    .filter(PasswordHistory.user_id == user_id)\
                    .order_by(PasswordHistory.created_at.desc())\
                    .all()
                
                # Delete entries beyond the limit
                if len(all_entries) > self.config.password_history_count:
                    for entry in all_entries[self.config.password_history_count:]:
                        db.delete(entry)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error saving password history: {e}")
            db.rollback()
            raise
    
    async def check_password_history(
        self,
        db: Session,
        user_id: str,
        new_password: str
    ) -> bool:
        """
        Check if password was used recently.
        
        Args:
            db: Database session
            user_id: User ID
            new_password: Plain text password to check
            
        Returns:
            True if password is in history (not allowed), False if OK to use
        """
        if self.config.password_history_count <= 0:
            return False
        
        from app.models.password_history import PasswordHistory
        
        try:
            # Get recent password history
            history_entries = db.query(PasswordHistory)\
                .filter(PasswordHistory.user_id == user_id)\
                .order_by(PasswordHistory.created_at.desc())\
                .limit(self.config.password_history_count)\
                .all()
            
            # Check against each historical password
            for entry in history_entries:
                if pwd_context.verify(new_password, entry.password_hash):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking password history: {e}")
            # Fail open - allow password if history check fails
            return False
    
    async def check_password_age(
        self,
        db: Session,
        user_id: str
    ) -> Tuple[bool, Optional[datetime]]:
        """
        Check if password has expired based on age.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Tuple of (is_expired, expiry_date)
        """
        if self.config.max_password_age_days <= 0:
            return False, None
        
        from app.models.user import User
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.password_changed_at:
                # No password change date recorded, assume it's old
                return True, datetime.utcnow()
            
            expiry_date = user.password_changed_at + timedelta(days=self.config.max_password_age_days)
            is_expired = datetime.utcnow() > expiry_date
            
            return is_expired, expiry_date
            
        except Exception as e:
            logger.error(f"Error checking password age: {e}")
            return False, None
    
    async def can_change_password(
        self,
        db: Session,
        user_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user can change password (minimum age requirement).
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Tuple of (can_change, reason_if_not)
        """
        if self.config.min_password_age_days <= 0:
            return True, None
        
        from app.models.user import User
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.password_changed_at:
                # No previous password change, allow it
                return True, None
            
            min_change_date = user.password_changed_at + timedelta(days=self.config.min_password_age_days)
            if datetime.utcnow() < min_change_date:
                hours_remaining = (min_change_date - datetime.utcnow()).total_seconds() / 3600
                return False, f"Password cannot be changed for another {hours_remaining:.1f} hours"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking password change eligibility: {e}")
            return True, None
    
    def generate_secure_password(self, length: int = 16) -> str:
        """
        Generate a cryptographically secure random password.
        
        Args:
            length: Password length (default 16)
            
        Returns:
            Secure random password
        """
        # Ensure minimum length
        length = max(length, self.config.min_length)
        
        # Character sets
        uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        numbers = "0123456789"
        special = self.config.special_chars
        
        # Ensure we meet minimum requirements
        password_chars = []
        
        # Add required minimums
        for _ in range(self.config.min_uppercase):
            password_chars.append(secrets.choice(uppercase))
        
        for _ in range(self.config.min_lowercase):
            password_chars.append(secrets.choice(lowercase))
        
        for _ in range(self.config.min_numbers):
            password_chars.append(secrets.choice(numbers))
        
        for _ in range(self.config.min_special):
            password_chars.append(secrets.choice(special))
        
        # Fill the rest with random characters from all sets
        all_chars = uppercase + lowercase + numbers + special
        remaining_length = length - len(password_chars)
        
        for _ in range(remaining_length):
            password_chars.append(secrets.choice(all_chars))
        
        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password_chars)
        
        return ''.join(password_chars)
    
    async def record_failed_attempt(
        self,
        user_identifier: str,
        ip_address: str
    ) -> Tuple[int, bool]:
        """
        Record a failed login attempt.
        
        Args:
            user_identifier: Email or username
            ip_address: IP address of attempt
            
        Returns:
            Tuple of (attempt_count, is_locked)
        """
        from app.core.auth_rate_limiter import get_auth_rate_limiter
        
        rate_limiter = get_auth_rate_limiter()
        return await rate_limiter.record_failed_attempt(user_identifier, ip_address)
    
    async def clear_failed_attempts(self, user_identifier: str) -> None:
        """Clear failed attempts after successful login."""
        from app.core.auth_rate_limiter import get_auth_rate_limiter
        
        rate_limiter = get_auth_rate_limiter()
        await rate_limiter.clear_failed_attempts(user_identifier)


# Global instance with default configuration
_password_policy = None


def get_password_policy(config: Optional[PasswordPolicyConfig] = None) -> PasswordPolicy:
    """Get the global PasswordPolicy instance."""
    global _password_policy
    if _password_policy is None or config is not None:
        _password_policy = PasswordPolicy(config)
    return _password_policy
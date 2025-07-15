"""
Unit tests for Two-Factor Authentication functionality.
"""
import pytest
from datetime import datetime, timedelta
import pyotp
import bcrypt
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.two_factor_service import two_factor_service
from app.routes.two_factor_auth import (
    generate_secret,
    generate_backup_codes,
    hash_backup_code,
    verify_backup_code
)
from app.models.user import User


class TestTwoFactorService:
    """Test the TwoFactorService class."""
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user with 2FA enabled."""
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.email = "test@example.com"
        user.two_factor_enabled = True
        user.two_factor_secret = pyotp.random_base32()
        user.two_factor_backup_codes = []
        user.two_factor_last_used = None
        return user
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = Mock(spec=Session)
        db.commit = Mock()
        return db
    
    @pytest.mark.asyncio
    async def test_verify_valid_totp_code(self, mock_user, mock_db):
        """Test verification of a valid TOTP code."""
        # Generate a valid code
        totp = pyotp.TOTP(mock_user.two_factor_secret)
        valid_code = totp.now()
        
        # Verify the code
        is_valid, is_backup, remaining = await two_factor_service.verify_2fa_code(
            mock_db, mock_user, valid_code
        )
        
        assert is_valid is True
        assert is_backup is False
        assert remaining == 0
        assert mock_user.two_factor_last_used is not None
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_verify_invalid_totp_code(self, mock_user, mock_db):
        """Test verification of an invalid TOTP code."""
        # Use an invalid code
        invalid_code = "000000"
        
        # Verify the code
        is_valid, is_backup, remaining = await two_factor_service.verify_2fa_code(
            mock_db, mock_user, invalid_code
        )
        
        assert is_valid is False
        assert is_backup is False
        assert remaining == 0
        assert mock_user.two_factor_last_used is None
        assert not mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_verify_backup_code(self, mock_user, mock_db):
        """Test verification of a valid backup code."""
        # Generate and hash a backup code
        backup_code = "ABCD1234"
        hashed_code = hash_backup_code(backup_code)
        mock_user.two_factor_backup_codes = [hashed_code, "other_hash"]
        
        # Verify the backup code
        is_valid, is_backup, remaining = await two_factor_service.verify_2fa_code(
            mock_db, mock_user, "ABCD-1234"  # With hyphen
        )
        
        assert is_valid is True
        assert is_backup is True
        assert remaining == 1  # One code was used
        assert len(mock_user.two_factor_backup_codes) == 1
        assert mock_user.two_factor_last_used is not None
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_verify_without_2fa_enabled(self, mock_db):
        """Test verification when 2FA is not enabled."""
        # Create user without 2FA
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.two_factor_enabled = False
        user.two_factor_secret = None
        
        # Try to verify
        is_valid, is_backup, remaining = await two_factor_service.verify_2fa_code(
            mock_db, user, "123456"
        )
        
        assert is_valid is False
        assert is_backup is False
        assert remaining == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_user, mock_db):
        """Test rate limiting for verification attempts."""
        # Reset rate limiter
        two_factor_service.verify_limiter.requests.clear()
        
        # Make multiple attempts
        for i in range(10):
            await two_factor_service.verify_2fa_code(
                mock_db, mock_user, "000000"
            )
        
        # 11th attempt should raise ValueError
        with pytest.raises(ValueError, match="Too many 2FA verification attempts"):
            await two_factor_service.verify_2fa_code(
                mock_db, mock_user, "000000"
            )
    
    def test_generate_totp_uri(self, mock_user):
        """Test TOTP URI generation."""
        uri = two_factor_service.generate_totp_uri(mock_user)
        
        assert uri.startswith("otpauth://totp/")
        assert mock_user.email in uri
        assert "AI%20Road%20Trip" in uri  # URL encoded issuer
        assert f"secret={mock_user.two_factor_secret}" in uri
    
    def test_is_valid_totp_secret(self):
        """Test TOTP secret validation."""
        # Valid secret
        valid_secret = pyotp.random_base32()
        assert two_factor_service.is_valid_totp_secret(valid_secret) is True
        
        # Invalid secret
        assert two_factor_service.is_valid_totp_secret("invalid!@#") is False
        assert two_factor_service.is_valid_totp_secret("") is False
        assert two_factor_service.is_valid_totp_secret("12345") is False


class TestTwoFactorHelpers:
    """Test helper functions for 2FA."""
    
    def test_generate_secret(self):
        """Test secret generation."""
        secret = generate_secret()
        
        assert len(secret) == 32  # Base32 encoded
        assert secret.isalnum()  # Only alphanumeric
        assert secret.isupper()  # Base32 uses uppercase
        
        # Should be valid for TOTP
        totp = pyotp.TOTP(secret)
        assert totp.now() is not None
    
    def test_generate_backup_codes(self):
        """Test backup code generation."""
        codes = generate_backup_codes(10)
        
        assert len(codes) == 10
        assert all(len(code) == 9 for code in codes)  # XXXX-XXXX format
        assert all("-" in code for code in codes)
        assert len(set(codes)) == 10  # All unique
        
        # Check format
        for code in codes:
            parts = code.split("-")
            assert len(parts) == 2
            assert len(parts[0]) == 4
            assert len(parts[1]) == 4
            assert parts[0].isalnum()
            assert parts[1].isalnum()
    
    def test_hash_and_verify_backup_code(self):
        """Test backup code hashing and verification."""
        code = "ABCD-1234"
        hashed = hash_backup_code(code)
        
        # Hash should be different from original
        assert hashed != code
        assert len(hashed) > len(code)
        
        # Should verify correctly
        assert verify_backup_code(code, [hashed]) == hashed
        assert verify_backup_code("ABCD1234", [hashed]) == hashed  # Without hyphen
        assert verify_backup_code("abcd-1234", [hashed]) is None  # Case sensitive
        assert verify_backup_code("WXYZ-5678", [hashed]) is None  # Wrong code
    
    def test_backup_code_security(self):
        """Test that backup codes use secure hashing."""
        code = "TEST-CODE"
        hash1 = hash_backup_code(code)
        hash2 = hash_backup_code(code)
        
        # Same code should produce different hashes (due to salt)
        assert hash1 != hash2
        
        # But both should verify
        assert verify_backup_code(code, [hash1]) == hash1
        assert verify_backup_code(code, [hash2]) == hash2


class TestTwoFactorIntegration:
    """Integration tests for 2FA flow."""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-agent"}
        return request
    
    def test_complete_2fa_flow(self):
        """Test the complete 2FA setup and verification flow."""
        # 1. Generate secret and backup codes
        secret = generate_secret()
        backup_codes = generate_backup_codes()
        hashed_codes = [hash_backup_code(code) for code in backup_codes]
        
        # 2. Create TOTP instance
        totp = pyotp.TOTP(secret)
        
        # 3. Generate QR provisioning URI
        uri = totp.provisioning_uri(
            name="test@example.com",
            issuer_name="AI Road Trip"
        )
        assert "otpauth://totp/" in uri
        
        # 4. Verify TOTP code
        code = totp.now()
        assert totp.verify(code, valid_window=1)
        
        # 5. Verify backup code
        assert verify_backup_code(backup_codes[0], hashed_codes) is not None
    
    def test_clock_drift_tolerance(self):
        """Test that TOTP allows for clock drift."""
        secret = generate_secret()
        totp = pyotp.TOTP(secret)
        
        # Get current code
        current_code = totp.now()
        
        # Code should be valid within window
        assert totp.verify(current_code, valid_window=1)
        
        # Test with past/future timestamps
        past_time = datetime.now() - timedelta(seconds=30)
        past_code = totp.at(past_time)
        assert totp.verify(past_code, valid_window=1)


@pytest.mark.parametrize("code,expected", [
    ("123456", True),  # Valid TOTP format
    ("12345", False),  # Too short
    ("1234567", False),  # Too long
    ("12345a", False),  # Contains letter
    ("ABCD-1234", True),  # Valid backup format
    ("ABCD1234", True),  # Backup without hyphen
    ("abcd-1234", True),  # Lowercase backup
    ("ABCD-12345", False),  # Invalid backup format
])
def test_code_format_validation(code, expected):
    """Test validation of different code formats."""
    if len(code) == 6:
        # TOTP validation
        is_valid = code.isdigit()
        assert is_valid == expected
    else:
        # Backup code validation
        clean = code.upper().replace("-", "")
        is_valid = len(clean) == 8 and clean.isalnum()
        assert is_valid == expected
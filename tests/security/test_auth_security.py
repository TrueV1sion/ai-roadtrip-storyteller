"""
Security tests for authentication rate limiting and account lockout.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from backend.app.core.auth_rate_limiter import AuthRateLimiter, get_auth_rate_limiter
from backend.app.services.account_security import AccountSecurityService, get_account_security_service
from backend.app.models.user import User


@pytest.fixture
async def auth_rate_limiter():
    """Create a test rate limiter instance"""
    limiter = AuthRateLimiter()
    # Mock the cache
    limiter.cache = AsyncMock()
    limiter._initialized = True
    return limiter


@pytest.fixture
async def account_security():
    """Create a test account security service"""
    service = AccountSecurityService()
    service.rate_limiter = AsyncMock()
    service._cache = AsyncMock()
    return service


@pytest.fixture
def mock_user():
    """Create a mock user"""
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.username = "testuser"
    user.is_admin = False
    user.two_factor_enabled = False
    user.two_factor_secret = None
    user.last_login = None
    return user


class TestAuthRateLimiter:
    """Test authentication rate limiting functionality"""
    
    async def test_rate_limit_allows_within_limit(self, auth_rate_limiter):
        """Test that requests within limit are allowed"""
        auth_rate_limiter.cache.get.return_value = "2"  # 2 previous attempts
        auth_rate_limiter.cache.ttl.return_value = 45
        
        allowed, ttl = await auth_rate_limiter.check_rate_limit(
            "login", "192.168.1.1"
        )
        
        assert allowed is True
        assert ttl is None
        auth_rate_limiter.cache.incr.assert_called_once()
    
    async def test_rate_limit_blocks_when_exceeded(self, auth_rate_limiter):
        """Test that requests are blocked when limit exceeded"""
        auth_rate_limiter.cache.get.return_value = "5"  # At limit
        auth_rate_limiter.cache.ttl.return_value = 30
        
        allowed, ttl = await auth_rate_limiter.check_rate_limit(
            "login", "192.168.1.1"
        )
        
        assert allowed is False
        assert ttl == 30
        auth_rate_limiter.cache.incr.assert_not_called()
    
    async def test_rate_limit_different_endpoints(self, auth_rate_limiter):
        """Test different rate limits for different endpoints"""
        # Test registration endpoint (3 per hour)
        auth_rate_limiter.cache.get.return_value = "2"
        
        allowed, _ = await auth_rate_limiter.check_rate_limit(
            "register", "192.168.1.1"
        )
        assert allowed is True
        
        # Exceed registration limit
        auth_rate_limiter.cache.get.return_value = "3"
        allowed, _ = await auth_rate_limiter.check_rate_limit(
            "register", "192.168.1.1"
        )
        assert allowed is False
    
    async def test_lockout_after_failed_attempts(self, auth_rate_limiter):
        """Test account lockout after threshold"""
        auth_rate_limiter.cache.get.return_value = "4"  # 4 previous attempts
        
        attempts, is_locked = await auth_rate_limiter.record_failed_attempt(
            "test@example.com", "192.168.1.1"
        )
        
        assert attempts == 5
        assert is_locked is True
        
        # Verify lockout was set
        auth_rate_limiter.cache.setex.assert_called()
        call_args = auth_rate_limiter.cache.setex.call_args_list
        
        # Check both user and IP lockout
        assert len(call_args) >= 2
        assert "auth_lockout:test@example.com" in str(call_args)
        assert "auth_lockout:192.168.1.1" in str(call_args)
    
    async def test_check_lockout_status(self, auth_rate_limiter):
        """Test checking if account is locked out"""
        # Not locked out
        auth_rate_limiter.cache.get.return_value = None
        is_locked, ttl = await auth_rate_limiter.check_lockout("test@example.com")
        assert is_locked is False
        assert ttl is None
        
        # Locked out
        auth_rate_limiter.cache.get.return_value = "5:192.168.1.1:2025-06-03T00:00:00"
        auth_rate_limiter.cache.ttl.return_value = 1200
        
        is_locked, ttl = await auth_rate_limiter.check_lockout("test@example.com")
        assert is_locked is True
        assert ttl == 1200
    
    async def test_unlock_account(self, auth_rate_limiter):
        """Test manually unlocking an account"""
        await auth_rate_limiter.unlock_account("test@example.com")
        
        # Verify both keys were deleted
        expected_calls = [
            (("auth_lockout:test@example.com",),),
            (("auth_failed:test@example.com",),)
        ]
        actual_calls = auth_rate_limiter.cache.delete.call_args_list
        assert len(actual_calls) == 2


class TestAccountSecurityService:
    """Test account security service functionality"""
    
    async def test_handle_failed_login(self, account_security, mock_user):
        """Test handling failed login attempts"""
        account_security.rate_limiter.record_failed_attempt.return_value = (3, False)
        account_security.rate_limiter.get_lockout_info.return_value = None
        
        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = mock_user
        
        result = await account_security.handle_failed_login(
            "test@example.com", "192.168.1.1", mock_db
        )
        
        assert result["attempts"] == 3
        assert result["is_locked"] is False
        assert "2 attempts remaining" in result["message"]
    
    async def test_handle_successful_login(self, account_security, mock_user):
        """Test handling successful login"""
        cache_mock = AsyncMock()
        account_security._cache = cache_mock
        cache_mock.get.return_value = None
        
        mock_db = MagicMock()
        
        await account_security.handle_successful_login(
            mock_user, "192.168.1.1", mock_db
        )
        
        # Verify failed attempts were cleared
        account_security.rate_limiter.clear_failed_attempts.assert_called_with(
            mock_user.email
        )
    
    async def test_generate_2fa_secret(self, account_security, mock_user):
        """Test 2FA secret generation"""
        secret = account_security.generate_2fa_secret(mock_user)
        
        assert isinstance(secret, str)
        assert len(secret) == 32  # Base32 encoded
    
    async def test_verify_2fa_token(self, account_security):
        """Test 2FA token verification"""
        import pyotp
        
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        valid_token = totp.now()
        
        # Valid token
        assert account_security.verify_2fa_token(secret, valid_token) is True
        
        # Invalid token
        assert account_security.verify_2fa_token(secret, "000000") is False
    
    async def test_generate_backup_codes(self, account_security):
        """Test backup code generation"""
        codes = account_security.generate_backup_codes(5)
        
        assert len(codes) == 5
        for code in codes:
            assert len(code) == 9  # XXXX-XXXX format
            assert code[4] == "-"
    
    async def test_enable_2fa(self, account_security, mock_user):
        """Test enabling 2FA for a user"""
        mock_db = MagicMock()
        secret = "TESTSECRET123456"
        backup_codes = ["AAAA-BBBB", "CCCC-DDDD"]
        
        cache_mock = AsyncMock()
        account_security._cache = cache_mock
        
        await account_security.enable_2fa(
            mock_user, secret, backup_codes, mock_db
        )
        
        assert mock_user.two_factor_secret == secret
        assert mock_user.two_factor_enabled is True
        assert mock_user.two_factor_backup_codes == "AAAA-BBBB,CCCC-DDDD"
        mock_db.commit.assert_called_once()
    
    async def test_admin_unlock_requires_admin(self, account_security, mock_user):
        """Test that admin unlock requires admin privileges"""
        mock_user.is_admin = False
        mock_db = MagicMock()
        
        with pytest.raises(PermissionError):
            await account_security.admin_unlock_account(
                "locked@example.com", mock_user, mock_db
            )
    
    async def test_get_security_status(self, account_security, mock_user):
        """Test getting comprehensive security status"""
        account_security.rate_limiter.get_lockout_info.return_value = {
            "attempts": 5,
            "ip_address": "192.168.1.1",
            "locked_at": "2025-06-03T00:00:00",
            "seconds_remaining": 900
        }
        
        status = await account_security.get_security_status(mock_user)
        
        assert status["two_factor_enabled"] is False
        assert status["is_locked_out"] is True
        assert status["lockout_info"]["attempts"] == 5


class TestSecurityIntegration:
    """Integration tests for security features"""
    
    async def test_progressive_lockout_messages(self, auth_rate_limiter, account_security):
        """Test progressive warning messages as attempts increase"""
        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None
        
        messages = []
        for attempt in range(1, 7):
            auth_rate_limiter.record_failed_attempt.return_value = (attempt, attempt >= 5)
            auth_rate_limiter.get_lockout_info.return_value = None if attempt < 5 else {
                "attempts": attempt
            }
            
            result = await account_security.handle_failed_login(
                "test@example.com", "192.168.1.1", mock_db
            )
            messages.append(result["message"])
        
        # First attempts should be generic
        assert messages[0] == "Invalid credentials."
        assert messages[1] == "Invalid credentials."
        
        # Later attempts should warn
        assert "attempts remaining" in messages[2]
        assert "attempts remaining" in messages[3]
        
        # Final attempt should lock out
        assert "locked" in messages[4].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
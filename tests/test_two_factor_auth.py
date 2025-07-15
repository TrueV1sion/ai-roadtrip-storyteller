"""
Test Two-Factor Authentication functionality
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
import pyotp
from datetime import datetime, timedelta

from app.core.security import get_password_hash
from app.models.user import User
from app.services.two_factor_service import two_factor_service


@pytest.fixture
async def user_with_2fa(db: Session):
    """Create a user with 2FA enabled."""
    user = User(
        email="2fa@example.com",
        username="2fauser",
        hashed_password=get_password_hash("test123"),
        is_active=True,
        two_factor_secret=two_factor_service.generate_secret(),
        two_factor_backup_codes=two_factor_service._generate_backup_codes()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
async def user_without_2fa(db: Session):
    """Create a user without 2FA."""
    user = User(
        email="no2fa@example.com",
        username="no2fauser",
        hashed_password=get_password_hash("test123"),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestTwoFactorAuth:
    """Test 2FA authentication flow."""
    
    async def test_login_without_2fa(self, client: AsyncClient, user_without_2fa: User):
        """Test normal login for user without 2FA."""
        response = await client.post(
            "/api/auth/token",
            data={
                "username": user_without_2fa.email,
                "password": "test123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] != ""
        assert "refresh_token" in data
        assert not data.get("requires_2fa", False)
        assert "partial_token" not in data
    
    async def test_login_with_2fa_returns_partial_token(self, client: AsyncClient, user_with_2fa: User):
        """Test login for user with 2FA returns partial token."""
        response = await client.post(
            "/api/auth/token",
            data={
                "username": user_with_2fa.email,
                "password": "test123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == ""  # Empty access token
        assert data["requires_2fa"] is True
        assert "partial_token" in data
        assert data["partial_token"] != ""
        assert "refresh_token" not in data
    
    async def test_complete_2fa_login_with_valid_totp(self, client: AsyncClient, user_with_2fa: User):
        """Test completing 2FA login with valid TOTP code."""
        # First, get partial token
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": user_with_2fa.email,
                "password": "test123"
            }
        )
        partial_token = login_response.json()["partial_token"]
        
        # Generate valid TOTP code
        totp = pyotp.TOTP(user_with_2fa.two_factor_secret)
        code = totp.now()
        
        # Complete 2FA login
        response = await client.post(
            "/api/auth/2fa/login",
            json={
                "partial_token": partial_token,
                "code": code
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] != ""
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    async def test_complete_2fa_login_with_backup_code(self, client: AsyncClient, user_with_2fa: User, db: Session):
        """Test completing 2FA login with backup code."""
        # First, get partial token
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": user_with_2fa.email,
                "password": "test123"
            }
        )
        partial_token = login_response.json()["partial_token"]
        
        # Use first backup code
        backup_code = user_with_2fa.two_factor_backup_codes[0]
        
        # Complete 2FA login
        response = await client.post(
            "/api/auth/2fa/login",
            json={
                "partial_token": partial_token,
                "code": backup_code
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] != ""
        
        # Verify backup code was used
        db.refresh(user_with_2fa)
        assert backup_code not in user_with_2fa.two_factor_backup_codes
    
    async def test_complete_2fa_login_with_invalid_code(self, client: AsyncClient, user_with_2fa: User):
        """Test completing 2FA login with invalid code."""
        # First, get partial token
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": user_with_2fa.email,
                "password": "test123"
            }
        )
        partial_token = login_response.json()["partial_token"]
        
        # Try with invalid code
        response = await client.post(
            "/api/auth/2fa/login",
            json={
                "partial_token": partial_token,
                "code": "123456"  # Invalid code
            }
        )
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid 2FA code"
    
    async def test_complete_2fa_login_with_invalid_partial_token(self, client: AsyncClient):
        """Test completing 2FA login with invalid partial token."""
        response = await client.post(
            "/api/auth/2fa/login",
            json={
                "partial_token": "invalid.token.here",
                "code": "123456"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid or expired partial token" in response.json()["detail"]
    
    async def test_partial_token_rejected_for_protected_endpoints(self, client: AsyncClient, user_with_2fa: User):
        """Test that partial tokens are rejected for protected endpoints."""
        # First, get partial token
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": user_with_2fa.email,
                "password": "test123"
            }
        )
        partial_token = login_response.json()["partial_token"]
        
        # Try to access protected endpoint with partial token
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {partial_token}"}
        )
        
        assert response.status_code == 401
        assert "2FA verification required" in response.json()["detail"]
    
    async def test_enable_2fa(self, client: AsyncClient, user_without_2fa: User):
        """Test enabling 2FA for a user."""
        # First login
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": user_without_2fa.email,
                "password": "test123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Enable 2FA
        response = await client.post(
            "/api/auth/2fa/enable",
            json={"password": "test123"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert "qr_code" in data
        assert "backup_codes" in data
        assert len(data["backup_codes"]) == 10
    
    async def test_verify_2fa_code(self, client: AsyncClient, user_with_2fa: User):
        """Test verifying 2FA code endpoint."""
        # Login to get full token (skip 2FA for test)
        user_with_2fa.two_factor_secret = None  # Temporarily disable
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": user_with_2fa.email,
                "password": "test123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Re-enable 2FA
        user_with_2fa.two_factor_secret = two_factor_service.generate_secret()
        
        # Generate valid TOTP
        totp = pyotp.TOTP(user_with_2fa.two_factor_secret)
        code = totp.now()
        
        # Verify code
        response = await client.post(
            "/api/auth/2fa/verify",
            json={"code": code},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is True
        assert data["backup_code_used"] is False
    
    async def test_disable_2fa(self, client: AsyncClient, user_with_2fa: User, db: Session):
        """Test disabling 2FA."""
        # Login (temporarily disable 2FA for login)
        original_secret = user_with_2fa.two_factor_secret
        user_with_2fa.two_factor_secret = None
        db.commit()
        
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": user_with_2fa.email,
                "password": "test123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Re-enable 2FA
        user_with_2fa.two_factor_secret = original_secret
        db.commit()
        
        # Generate valid TOTP
        totp = pyotp.TOTP(user_with_2fa.two_factor_secret)
        code = totp.now()
        
        # Disable 2FA
        response = await client.post(
            "/api/auth/2fa/disable",
            json={
                "password": "test123",
                "code": code
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 204
        
        # Verify 2FA is disabled
        db.refresh(user_with_2fa)
        assert user_with_2fa.two_factor_secret is None
        assert user_with_2fa.two_factor_backup_codes is None
    
    async def test_2fa_status(self, client: AsyncClient, user_with_2fa: User):
        """Test getting 2FA status."""
        # Login (temporarily disable 2FA)
        user_with_2fa.two_factor_secret = None
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": user_with_2fa.email,
                "password": "test123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Re-enable 2FA
        user_with_2fa.two_factor_secret = two_factor_service.generate_secret()
        
        # Get status
        response = await client.get(
            "/api/auth/2fa/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["backup_codes_count"] == len(user_with_2fa.two_factor_backup_codes)
    
    async def test_regenerate_backup_codes(self, client: AsyncClient, user_with_2fa: User, db: Session):
        """Test regenerating backup codes."""
        # Login (temporarily disable 2FA)
        original_secret = user_with_2fa.two_factor_secret
        original_codes = user_with_2fa.two_factor_backup_codes.copy()
        user_with_2fa.two_factor_secret = None
        db.commit()
        
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": user_with_2fa.email,
                "password": "test123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Re-enable 2FA
        user_with_2fa.two_factor_secret = original_secret
        db.commit()
        
        # Generate valid TOTP
        totp = pyotp.TOTP(user_with_2fa.two_factor_secret)
        code = totp.now()
        
        # Regenerate backup codes
        response = await client.post(
            "/api/auth/2fa/backup-codes",
            json={
                "password": "test123",
                "code": code
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["backup_codes"]) == 10
        assert data["backup_codes"] != original_codes  # New codes generated
    
    async def test_rate_limiting_2fa_attempts(self, client: AsyncClient, user_with_2fa: User):
        """Test rate limiting on 2FA attempts."""
        # Get partial token
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": user_with_2fa.email,
                "password": "test123"
            }
        )
        partial_token = login_response.json()["partial_token"]
        
        # Make multiple failed attempts
        for i in range(6):  # Exceed rate limit
            response = await client.post(
                "/api/auth/2fa/login",
                json={
                    "partial_token": partial_token,
                    "code": "000000"  # Invalid code
                }
            )
            
            if i < 5:
                assert response.status_code == 401
            else:
                # Should be rate limited
                assert response.status_code == 429
                assert "Too many failed attempts" in response.json()["detail"]